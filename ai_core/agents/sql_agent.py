from langchain_core.prompts import ChatPromptTemplate

from ai_core.llm.ollama_client import llm

#from ai_core.tools.sql_tool import execute_sql_query


SQL_SYSTEM_PROMPT = """
You are an expert SQL generation agent.

Your job:
1. Convert user question into SQL query
2. Use only available schema
3. Never hallucinate columns
4. Generate safe SELECT-only queries
5. Never generate DELETE, UPDATE, DROP, ALTER

Schema:

TABLE products:
- id
- product_name
- category
- brand
- price
- description
- inverter
- wifi_enabled
- smart_features
- rating
- review_count
- stock

TABLE air_conditioners:
- product_id
- cooling_capacity_btu
- heating_capacity_btu
- cooling_power_w
- heating_power_w
- eer
- cop
- indoor_noise_db
- outdoor_noise_db
- refrigerant_type

TABLE reviews:
- id
- product_id
- rating
- review_text
- sentiment
- review_date

Rules:
- Return ONLY SQL
- Use LIMIT where appropriate
- Use JOINS correctly
- Use LOWER() for text matching
"""


prompt = ChatPromptTemplate.from_messages([
    ("system", SQL_SYSTEM_PROMPT),
    ("human", "{query}")
])


sql_chain = prompt | llm



def sql_agent(state):

    user_query = state["user_query"]

    response = sql_chain.invoke({
        "query": user_query
    })

    sql_query = response.content.strip()

    sql_result = execute_sql_query(sql_query)

    return {
        "tool_output": str(sql_result)
    }