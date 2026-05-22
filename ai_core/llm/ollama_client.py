from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="llama3.2:1b",
    temperature=0
)

query = input("Ask Some Question:")
while query != "/bye":
    response = llm.invoke(query)
    print(response.content)
    query = input("Ask Some Question:")

print ("llama closed successfully")