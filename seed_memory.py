

import asyncio
import uuid
from vanna_setup import agent_memory
from vanna.core.tool import ToolContext
from vanna.core.user import User
# ── Minimal fake context needed by save_tool_usage ────────────────────────────

def make_context() -> ToolContext:
    user = User(id="seed", email="seed@clinic.local", group_memberships=["admin"])
    return ToolContext(
        user=user,
        conversation_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        agent_memory=agent_memory,
    )

# ── Q&A pairs ─────────────────────────────────────────────────────────────────

QA_PAIRS = [
    # --- Patient queries ---
    (
        "How many patients do we have?",
        "SELECT COUNT(*) AS total_patients FROM patients;",
    ),
    (
        "List all patients with their city and gender",
        "SELECT first_name, last_name, city, gender FROM patients ORDER BY last_name;",
    ),
    (
        "How many male and female patients do we have?",
        "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender;",
    ),
    (
        "Which city has the most patients?",
        """SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC
LIMIT 1;""",
    ),
    (
        "Show patient count by city",
        """SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC;""",
    ),
    # --- Doctor queries ---
    (
        "List all doctors and their specializations",
        "SELECT name, specialization, department FROM doctors ORDER BY specialization, name;",
    ),
    (
        "Which doctor has the most appointments?",
        """SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count
FROM doctors d
JOIN appointments a ON a.doctor_id = d.id
GROUP BY d.id, d.name, d.specialization
ORDER BY appointment_count DESC
LIMIT 1;""",
    ),
    (
        "Show revenue by doctor",
        """SELECT d.name, d.specialization, ROUND(SUM(i.total_amount), 2) AS total_revenue
FROM invoices i
JOIN appointments a ON a.patient_id = i.patient_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name, d.specialization
ORDER BY total_revenue DESC;""",
    ),
    # --- Appointment queries ---
    (
        "Show me appointments for last month",
        """SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name,
       d.name AS doctor_name, a.appointment_date, a.status
FROM appointments a
JOIN patients p ON p.id = a.patient_id
JOIN doctors  d ON d.id = a.doctor_id
WHERE strftime('%Y-%m', a.appointment_date) =
      strftime('%Y-%m', date('now','-1 month'))
ORDER BY a.appointment_date;""",
    ),
    (
        "How many cancelled appointments last quarter?",
        """SELECT COUNT(*) AS cancelled_count
FROM appointments
WHERE status = 'Cancelled'
  AND appointment_date >= date('now','-3 months');""",
    ),
    (
        "Show monthly appointment count for the past 6 months",
        """SELECT strftime('%Y-%m', appointment_date) AS month,
       COUNT(*) AS appointment_count
FROM appointments
WHERE appointment_date >= date('now','-6 months')
GROUP BY month
ORDER BY month;""",
    ),
    # --- Financial queries ---
    (
        "What is the total revenue?",
        "SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices;",
    ),
    (
        "Show unpaid invoices",
        """SELECT i.id, p.first_name || ' ' || p.last_name AS patient_name,
       i.invoice_date, i.total_amount,
       i.total_amount - i.paid_amount AS balance_due, i.status
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status IN ('Pending','Overdue')
ORDER BY i.status, i.invoice_date;""",
    ),
    (
        "Average treatment cost by specialization",
        """SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.specialization
ORDER BY avg_cost DESC;""",
    ),
    # --- Time-based queries ---
    (
        "Show patient registration trend by month",
        """SELECT strftime('%Y-%m', registered_date) AS month,
       COUNT(*) AS new_patients
FROM patients
GROUP BY month
ORDER BY month;""",
    ),
    # --- Advanced ---
    (
        "Top 5 patients by total spending",
        """SELECT p.first_name, p.last_name,
       ROUND(SUM(i.total_amount), 2) AS total_spending
FROM invoices i
JOIN patients p ON p.id = i.patient_id
GROUP BY p.id, p.first_name, p.last_name
ORDER BY total_spending DESC
LIMIT 5;""",
    ),
    (
        "List patients who visited more than 3 times",
        """SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count
FROM appointments a
JOIN patients p ON p.id = a.patient_id
GROUP BY p.id, p.first_name, p.last_name
HAVING visit_count > 3
ORDER BY visit_count DESC;""",
    ),
    (
        "What percentage of appointments are no-shows?",
        """SELECT ROUND(
  100.0 * SUM(CASE WHEN status='No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2
) AS no_show_pct
FROM appointments;""",
    ),
    (
        "Show the busiest day of the week for appointments",
        """SELECT
  CASE strftime('%w', appointment_date)
    WHEN '0' THEN 'Sunday'   WHEN '1' THEN 'Monday'
    WHEN '2' THEN 'Tuesday'  WHEN '3' THEN 'Wednesday'
    WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
    WHEN '6' THEN 'Saturday'
  END AS day_of_week,
  COUNT(*) AS appointment_count
FROM appointments
GROUP BY strftime('%w', appointment_date)
ORDER BY appointment_count DESC
LIMIT 1;""",
    ),
    (
        "Revenue trend by month",
        """SELECT strftime('%Y-%m', invoice_date) AS month,
       ROUND(SUM(total_amount), 2) AS revenue
FROM invoices
GROUP BY month
ORDER BY month;""",
    ),
]


async def seed():
    print(f"Seeding {len(QA_PAIRS)} Q&A pairs into DemoAgentMemory ...")
    ctx = make_context()
    ok = 0

    for i, (question, sql) in enumerate(QA_PAIRS, 1):
        try:
            await agent_memory.save_tool_usage(
                question=question,
                tool_name="RunSqlTool",
                args={"sql": sql},
                context=ctx,
                success=True,
            )
            print(f"  [{i:02d}] ok  {question[:65]}")
            ok += 1
        except Exception as exc:
            print(f"  [{i:02d}] FAIL  {question[:65]}\n       Error: {exc}")

    total = len(agent_memory._memories)
    print(f"\nSeeded {ok}/{len(QA_PAIRS)} pairs successfully.")
    print(f"Total items in memory: {total}")


if __name__ == "__main__":
    asyncio.run(seed())
