from ai_core.agents.python_agent import generate_sql_query
query = generate_sql_query("make a chart of all washing machines wrt to the prices", "washing_machines")
print("GENERATED SQL:", query)
