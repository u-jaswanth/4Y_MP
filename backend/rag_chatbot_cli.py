"""
Standalone terminal chatbot for testing the RAG pipeline directly,
without going through the FastAPI backend or a specific patient.

Run from the backend/ directory:

    python rag_chatbot_cli.py

Note: this queries the ENTIRE observation index (all patients),
since there is no logged-in user here. Use it for pipeline testing
only - the real product surface is the "/chat" API used by the
frontend's AI Chat tab, which is scoped to the logged-in patient's
own analyzed reports.
"""

from app.retrieval.combined_retriever import CombinedRetriever
from app.retrieval.query_router import QueryRouter
from app.generation.context_builder import RAGContextBuilder
from app.generation.answer_generator import MedicalAnswerGenerator
from app.vectorstore.bootstrap import ensure_pgvector_extension


def main():

    ensure_pgvector_extension()

    retriever = CombinedRetriever(
        patient_top_k=5,
        knowledge_top_k=5
    )

    router = QueryRouter()

    context_builder = RAGContextBuilder()
    generator = MedicalAnswerGenerator()

    print("================================")
    print("       MEDICONNECT RAG")
    print("================================")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:

        query = input("You: ").strip()

        if query.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not query:
            continue

        route = router.route(query)
        comprehensive = route["scope"] == "comprehensive"

        retrieval_result = retriever.retrieve(query, comprehensive=comprehensive)

        patient = retrieval_result.get("patient", {})
        observations = patient.get("observations", [])
        knowledge = retrieval_result.get("knowledge", [])

        print(f"[ROUTER] Scope: {route['scope']}")
        print(f"[RETRIEVAL] Patient observations: {len(observations)}")
        print(f"[RETRIEVAL] Knowledge chunks: {len(knowledge)}")

        if not observations and not knowledge:
            print(
                "\nMediConnect: I couldn't find relevant information "
                "in the available medical records or medical knowledge base.\n"
            )
            continue

        context = context_builder.build(query=query, retrieval_result=retrieval_result)
        answer = generator.generate(query=query, retrieved_context=context)

        print("\nMediConnect:", answer)
        print()


if __name__ == "__main__":
    main()
