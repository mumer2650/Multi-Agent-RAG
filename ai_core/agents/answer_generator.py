from ai_core.llm.ollama_client import llm

# ── Formatting helpers ─────────────────────────────────────────────────────────

# Internal DB fields that should never appear in user-facing output
_SKIP_FIELDS  = {'id', 'product_id', 'category_id', 'embedding_id'}
# Fields whose values are monetary (get Rs prefix + comma formatting)
_MONEY_FIELDS = {'price', 'original_price', 'sale_price', 'standard_annual_cost', 'efficient_annual_cost', 'annual_savings', 'price_premium', 'annual_cost_rs', 'monthly_cost_rs'}


def format_pk_rupees(amount) -> str:
    """Format numbers using Pakistani/Indian numbering system (Lakhs/Crores)."""
    try:
        amount = int(float(amount))
        s = str(amount)
        if len(s) <= 3:
            return s
        last_three = s[-3:]
        rest = s[:-3]
        chunks = []
        while len(rest) > 2:
            chunks.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.append(rest)
        chunks.reverse()
        return ",".join(chunks) + "," + last_three
    except (ValueError, TypeError):
        return str(amount)

def _fmt_value(key: str, val) -> str:
    """Render a single key-value pair as a human-readable string."""
    label = key.replace('_', ' ').title()
    if key in _MONEY_FIELDS and isinstance(val, (int, float)):
        return f"{label}: Rs {format_pk_rupees(val)}"
    if isinstance(val, float):
        return f"{label}: {val:.2f}"
    return f"{label}: {val}"


def _render_sql_rows(sql_data: list, action: str) -> str:
    """
    Build the final answer string from SQL rows.

    Replaces the old hardcoded formatter that only showed model_name + price
    and ignored all other columns (causing missing average_rating, count, etc.)

    Handles three patterns:

    Pattern 1 — Pure aggregate (single summary row, no GROUP BY):
      e.g. {'model_name': 'Samsung ACs with Wi-Fi', 'count': 3}
      → "Samsung ACs with Wi-Fi: 3"

    Pattern 2 — Category-level grouped rows:
      e.g. {'model_name': 'dishwashers', 'average_rating': 4.67}
      → "• dishwashers — Average Rating: 4.67"

    Pattern 3 — Normal per-product rows:
      e.g. {'model_name': 'Galaxy Buds FE', 'price': 25999}
      → "• Galaxy Buds FE — Price: Rs 25,999"
    """
    if not sql_data:
        return ""

    # ── Pattern 1: single aggregate row ───────────────────────────────────────
    if action == "aggregate" and len(sql_data) == 1:
        row   = sql_data[0]
        label = row.get('model_name', 'Result')
        extras = {
            k: v for k, v in row.items()
            if k != 'model_name' and k not in _SKIP_FIELDS and v is not None
        }
        if not extras:
            return label

        parts = []
        for key, val in extras.items():
            if key == 'count' and isinstance(val, (int, float)):
                # "Samsung ACs with Wi-Fi: 3"  (just the number, no label clutter)
                parts.append(str(int(val)))
            elif isinstance(val, float):
                parts.append(f"{val:.2f}")
            else:
                parts.append(str(val))

        return f"{label}: {', '.join(parts)}"

    # ── Patterns 2 & 3: multi-row results ─────────────────────────────────────
    rows_out = []
    for row in sql_data:
        model_name = row.get('model_name', 'Result')
        extras = {
            k: v for k, v in row.items()
            if k != 'model_name' and k not in _SKIP_FIELDS and v is not None
        }
        if extras:
            detail = ', '.join(_fmt_value(k, v) for k, v in extras.items())
            rows_out.append(f"- **{model_name}** — {detail}")
        else:
            rows_out.append(f"- **{model_name}**")

    n = len(sql_data)
    # Use a product-specific header if any row has a price, otherwise generic
    has_price = any('price' in row for row in sql_data)
    if has_price:
        header = f"Found {n} product{'s' if n != 1 else ''} matching your criteria:"
    else:
        header = f"Here are the results ({n} {'entry' if n == 1 else 'entries'}):"

    return header + "\n\n" + "\n".join(rows_out)


# ── Legacy large-result summariser (unchanged) ─────────────────────────────────

def _summarize_sql_results(sql_data: list) -> str:
    if not sql_data:
        return ""

    num_rows = len(sql_data)

    if num_rows >= 100:
        prices  = [r.get('price')  for r in sql_data if isinstance(r.get('price'),  (int, float))]
        ratings = [r.get('rating') for r in sql_data if isinstance(r.get('rating'), (int, float))]

        summary = f"Found {num_rows} products matching your criteria.\n\n"
        if prices:
            summary += f"Price Range: Rs {min(prices):,} - Rs {max(prices):,}\n"
            summary += f"Average Price: Rs {sum(prices)/len(prices):,.0f}\n"
        if ratings:
            summary += f"Rating Range: {min(ratings):.1f} - {max(ratings):.1f}/5\n"
            summary += f"Average Rating: {sum(ratings)/len(ratings):.1f}/5\n"
        summary += "\nTop 10 products:\n"
        key_fields = ['model_name', 'price', 'rating', 'id', 'category_name', 'spec_name', 'spec_value']
        for row in sql_data[:10]:
            summary += f"- { {k: v for k, v in row.items() if k in key_fields} }\n"
        if num_rows > 10:
            summary += f"\n... and {num_rows - 10} more products available\n"
        return summary

    elif num_rows > 20:
        summary = f"Found {num_rows} products. Showing key details:\n\n"
        for row in sql_data:
            summary += "- "
            for key in ['model_name', 'price', 'rating', 'has_inverter', 'spec_name', 'spec_value']:
                if key in row:
                    summary += f"{key}: {row[key]}, "
            summary = summary.rstrip(", ") + "\n"
        return summary

    else:
        summary = f"Found {num_rows} products:\n\n"
        for row in sql_data:
            summary += "- "
            for key in ['model_name', 'price', 'rating', 'has_inverter', 'energy_rating', 'spec_name', 'spec_value']:
                if key in row:
                    summary += f"{key}: {row[key]}, "
            summary = summary.rstrip(", ") + "\n"
        return summary


def _format_sql_results(sql_data: list, fields=None) -> str:
    if not sql_data:
        return ""
    if fields is None:
        fields = ['model_name', 'price', 'rating', 'has_inverter', 'energy_rating']
    lines = []
    for row in sql_data:
        parts = [str(row[k]) for k in fields if k in row]
        lines.append("- " + ", ".join(parts) if parts else f"- {row}")
    return "\n".join(lines)


# ── Main node ──────────────────────────────────────────────────────────────────

def answer_generator(state):

    docs        = state.get("retrieved_docs", [])
    tool_output = state.get("tool_output", {})
    user_query  = state.get("user_query", "")
    messages    = state.get("messages", [])[-6:]
    chart       = None
    context     = ""

    if tool_output and tool_output.get("type") == "sql_result":
        print(f"[DEBUG] answer_generator received SQL results: "
              f"{len(tool_output.get('data', []))} rows")

    # ── Tool output ────────────────────────────────────────────────────────────

    if isinstance(tool_output, dict):
        tool_type = tool_output.get("type")

        # ── Python result ──────────────────────────────────────────────────────
        if tool_type == "python_result":
            chart    = tool_output.get("chart")
            analysis = tool_output.get("analysis", [])
            
            # If we generated a chart, keep it in the state but STILL let the LLM generate a summary
            # We append the data to the context so the LLM can talk about it!
            if chart:
                context += f"\n\n[SYSTEM NOTE: A {chart.get('chartType')} chart was generated successfully for the user. Here is the raw data used for the chart so you can summarize/describe it:]\n"
                context += str(tool_output.get("data", analysis))[:100000] # Increase limit significantly to ensure all products with large feature texts fit
            
            # If the analysis is just a string message (e.g., "Need at least 2 products..."), 
            # return it directly to prevent the LLM from hallucinating python code examples.
            if isinstance(analysis, str) and not chart:
                return {
                    "final_answer": analysis,
                    "chart": None
                }
            
            # If analysis is a list of dictionaries, format it nicely and pass to LLM
            if isinstance(analysis, list) and len(analysis) > 0 and isinstance(analysis[0], dict) and not chart:
                lines = ["Based on the python analysis, here are the calculated results:"]
                for item in analysis:
                    model = item.get("model", item.get("model_name", "Result"))
                    details = []
                    for k, v in item.items():
                        if k not in ["model", "model_name"] and v is not None:
                            details.append(_fmt_value(k, v))
                    if details:
                        lines.append(f"- **{model}** — {', '.join(details)}")
                    else:
                        lines.append(f"- **{model}**")
                
                context += "\n\nPYTHON ANALYSIS:\n" + "\n".join(lines)

            elif isinstance(analysis, dict) and not chart:
                lines = ["Based on the python analysis, here are the calculated results:"]
                for k, v in analysis.items():
                    if v is not None:
                        lines.append(f"- **{k}** — {_fmt_value(k, v)}")
                
                context += "\n\nPYTHON ANALYSIS:\n" + "\n".join(lines)
                
            else:
                context += "\n\nPYTHON ANALYSIS:\n" + str(analysis)

        # ── SQL result ─────────────────────────────────────────────────────────
        elif tool_type == "sql_result":
            sql_data   = tool_output.get("data", [])
            sql_action = tool_output.get("action", "data_found")

            # Empty result — exit early
            if not sql_data:
                return {
                    "final_answer": (
                        "No matching products were found in the database "
                        "for your query. Please try a different search "
                        "term or category."
                    ),
                    "chart": None
                }

            # ── Small result sets (≤ 20 rows): render nicely and pass to LLM ──
            if len(sql_data) <= 20:
                context += "\n\nSQL RESULTS:\n" + _render_sql_rows(sql_data, sql_action)
            # Large result sets: summarise and pass to LLM
            else:
                context += "\n\nSQL RESULTS:\n" + _summarize_sql_results(sql_data)

        # ── Generic tool output ────────────────────────────────────────────────
        else:
            if tool_output:
                context += "\n\nTOOL OUTPUT:\n" + str(tool_output)

    else:
        if tool_output:
            context += "\n\nTOOL OUTPUT:\n" + str(tool_output)

    # ── Retrieval docs ─────────────────────────────────────────────────────────

    for index, doc in enumerate(docs[:3]):
        if not isinstance(doc, dict):
            continue
        source = doc.get('source', 'unknown')
        page   = doc.get('page', 'N/A')
        context += (
            f"\n\nDocument {index + 1}"
            f" [Source: {source}, Page: {page}]"
            f"\nContent:\n{doc.get('text', '')}"
        )

    # ── Empty context fallback ─────────────────────────────────────────────────

    print(f"[DEBUG] Before empty check - Context length: {len(context)}, "
          f"stripped: {len(context.strip())}")

    selected_agent = state.get("selected_agent", "")
    
    if not context.strip() and selected_agent != "answer":
        system_prompt = """
You are an expert, helpful AI assistant.
The user has asked a question, but no relevant information was found in the retrieved company documents or internal database.

INSTRUCTIONS:
1. First, explicitly state that you could not find the answer in the provided documents/database.
2. Politely inform the user that you do not have access to that information.
3. Do NOT guess, hallucinate, or attempt to answer the question based on general knowledge.
4. IMPORTANT: You must ONLY answer in English, regardless of the language the user's question is written in.

Be extremely careful. Do not invent features, prices, policies, or internal data. Answer clearly and concisely.
"""
        try:
            prompt_messages = [("system", system_prompt)]
            for m in messages:
                role = m.get("role") if isinstance(m, dict) else m.type
                content = m.get("content") if isinstance(m, dict) else m.content
                if role in ("user", "human"):
                    role = "human"
                elif role in ("assistant", "model", "ai"):
                    role = "ai"
                prompt_messages.append((role, content))
            
            if not messages:
                prompt_messages.append(("human", f"Question:\n{user_query}"))
                
            response = llm.invoke(prompt_messages)
            
            # Helper to extract string from Gemini list output
            content = response.content
            if isinstance(content, list):
                content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
            else:
                content = str(content)
                
            return {"final_answer": content, "chart": None}
        except Exception as error:
            return {"final_answer": f"Error generating answer: {str(error)}", "chart": None, "error": str(error)}
    # ── System prompt ──────────────────────────────────────────────────────────

    selected_agent = state.get("selected_agent", "")

    if tool_output and tool_output.get("type") == "sql_result":
        system_prompt = (
            "You are a helpful assistant. Answer the user's question based on "
            "the provided data. Be concise and clear."
        )
    elif selected_agent == "answer":
        system_prompt = """
You are Sage AI, the official assistant for Sage Appliances.
The user is engaging in general conversation, greetings, or asking about your identity.
You are permitted to answer these questions politely and naturally. 
You do NOT need to append "I do not have that information in my database" for conversational pleasantries or questions about your identity.
Keep your answers brief, friendly, and helpful.
"""
    else:
        system_prompt = """
You are an ecommerce AI assistant.

Answer ONLY from provided context.

If SQL results exist:
- summarize products clearly

If Python Analysis exists:
- You MUST list EVERY SINGLE product or row provided in the analysis.
- NEVER omit, skip, or summarize products out of laziness. 

If retrieved documents exist:
- answer clearly and completely based on the document content
- DO NOT manually write out source citations like '[Source: ...]' in your text. The system will automatically attach the sources to the UI.

Do not hallucinate. Do not invent information not present in the context.
If the context does not contain enough information, say so clearly.

You are Sage AI, the official assistant for Sage Appliances.
You will be provided with context from our database or manuals.
You MUST base your entire answer ONLY on the provided context.
If the context is empty or does not contain the answer, you must say 'I do not have that information in my database.'
DO NOT invent product names, prices, or car models.

IMPORTANT FORMATTING RULES:
1. You must ONLY answer in English, regardless of the language the user's question is written in.
2. ALL prices are in Pakistani Rupees (PKR). You MUST format prices as 'Rs' (e.g. Rs 120,000). NEVER use the dollar sign ($).
"""

    user_prompt = f"Question:\n{user_query}\n\nContext:\n{context}"

    # ── LLM call ───────────────────────────────────────────────────────────────

    if "SQL RESULTS" in context:
        print(f"[DEBUG] Context length: {len(context)} chars")
        print(f"[DEBUG] Context preview: {context[:200]}...")

    def _extract_content(response) -> str:
        content = response.content
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
        return str(content)

    print(f"[DEBUG] Sending to LLM - System prompt length: {len(system_prompt)}")
    print(f"[DEBUG] User prompt length: {len(user_prompt)}")
    print(f"[DEBUG] User prompt: {user_prompt[:150]}...")

    try:
        invoke_messages = [("system", system_prompt)]
        for m in messages:
            role = m.get("role") if isinstance(m, dict) else m.type
            content = m.get("content") if isinstance(m, dict) else m.content
            if role in ("user", "human"):
                role = "human"
            elif role in ("assistant", "model", "ai"):
                role = "ai"
            invoke_messages.append((role, content))
        invoke_messages.append(("human", user_prompt))
        
        response = llm.invoke(invoke_messages)
        return {"final_answer": _extract_content(response), "chart": chart}
    except Exception as error:
        return {"final_answer": f"Error generating answer: {str(error)}", "chart": chart, "error": str(error)}