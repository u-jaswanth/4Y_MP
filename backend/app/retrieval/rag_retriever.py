# # from app.retrieval.observation_index import ObservationIndex
# # from app.vectorstore.chroma_store import ChromaVectorStore


# # class RAGRetriever:

# #     def __init__(
# #         self,
# #         observation_top_k: int = 5
# #     ):

# #         self.observation_index = (
# #             ObservationIndex()
# #         )

# #         self.document_store = (
# #             ChromaVectorStore()
# #         )

# #         self.observation_top_k = (
# #             observation_top_k
# #         )


# #     def retrieve(
# #         self,
# #         query: str
# #     ):

# #         observation_results = (
# #             self.observation_index.search(
# #                 query,
# #                 top_k=self.observation_top_k
# #             )
# #         )

# #         documents = (
# #             observation_results
# #             .get("documents", [[]])[0]
# #         )

# #         metadatas = (
# #             observation_results
# #             .get("metadatas", [[]])[0]
# #         )

# #         distances = (
# #             observation_results
# #             .get("distances", [[]])[0]
# #         )

# #         hybrid_scores = (
# #             observation_results
# #             .get("hybrid_scores", [[]])[0]
# #         )

# #         observations = []

# #         for i in range(len(documents)):

# #             observations.append({
# #                 "document": documents[i],
# #                 "metadata": metadatas[i],
# #                 "distance": distances[i],
# #                 "hybrid_score": (
# #                     hybrid_scores[i]
# #                     if i < len(hybrid_scores)
# #                     else None
# #                 )
# #             })


# #         # --------------------------------
# #         # Find unique documents
# #         # --------------------------------

# #         document_ids = []

# #         for observation in observations:

# #             document_id = (
# #                 observation["metadata"]
# #                 .get("document_id")
# #             )

# #             if (
# #                 document_id
# #                 and document_id not in document_ids
# #             ):
# #                 document_ids.append(
# #                     document_id
# #                 )


# #         # --------------------------------
# #         # Retrieve complete documents
# #         # --------------------------------

# #         full_documents = []

# #         for document_id in document_ids:

# #             document = (
# #                 self.document_store.get_document(
# #                     document_id
# #                 )
# #             )

# #             if document:

# #                 full_documents.append(
# #                     document
# #                 )


# #         return {
# #             "query": query,
# #             "observations": observations,
# #             "documents": full_documents
# #         }

# from app.retrieval.observation_index import ObservationIndex
# from app.vectorstore.chroma_store import ChromaVectorStore


# class RAGRetriever:

#     def __init__(
#         self,
#         observation_top_k: int = 5,
#         embedder=None
#     ):

#         self.observation_index = (
#             ObservationIndex(
#                 embedder=embedder
#             )
#         )

#         self.document_store = (
#             ChromaVectorStore()
#         )

#         self.observation_top_k = (
#             observation_top_k
#         )

#     def retrieve(
#         self,
#         query: str
#     ):

#         observation_results = (
#             self.observation_index.search(
#                 query,
#                 top_k=self.observation_top_k
#             )
#         )

#         documents = (
#             observation_results
#             .get("documents", [[]])[0]
#         )

#         metadatas = (
#             observation_results
#             .get("metadatas", [[]])[0]
#         )

#         distances = (
#             observation_results
#             .get("distances", [[]])[0]
#         )

#         hybrid_scores = (
#             observation_results
#             .get("hybrid_scores", [[]])[0]
#         )

#         observations = []

#         for i in range(len(documents)):

#             observations.append({
#                 "document": documents[i],
#                 "metadata": metadatas[i],
#                 "distance": distances[i],
#                 "hybrid_score": (
#                     hybrid_scores[i]
#                     if i < len(hybrid_scores)
#                     else None
#                 )
#             })

#         # --------------------------------
#         # Find unique documents
#         # --------------------------------

#         document_ids = []

#         for observation in observations:

#             document_id = (
#                 observation["metadata"]
#                 .get("document_id")
#             )

#             if (
#                 document_id
#                 and document_id not in document_ids
#             ):
#                 document_ids.append(
#                     document_id
#                 )

#         # --------------------------------
#         # Retrieve complete documents
#         # --------------------------------

#         full_documents = []

#         for document_id in document_ids:

#             document = (
#                 self.document_store.get_document(
#                     document_id
#                 )
#             )

#             if document:

#                 full_documents.append(
#                     document
#                 )

#         return {
#             "query": query,
#             "observations": observations,
#             "documents": full_documents
#         }



from app.retrieval.observation_index import ObservationIndex
from app.vectorstore.pgvector_store import PgVectorStore


class RAGRetriever:

    def __init__(
        self,
        observation_top_k: int = 5,
        embedder=None
    ):

        self.observation_index = ObservationIndex(
            embedder=embedder
        )

        self.document_store = PgVectorStore()

        self.observation_top_k = observation_top_k

    def retrieve(
        self,
        query: str,
        comprehensive: bool = False,
        document_ids: list[str] | None = None
    ):

        # --------------------------------
        # Decide retrieval size
        # --------------------------------

        if comprehensive:
            top_k = self.observation_index.count()
        else:
            top_k = self.observation_top_k

        observation_results = (
            self.observation_index.search(
                query,
                top_k=top_k,
                document_ids=document_ids
            )
        )

        documents = observation_results.get(
            "documents", [[]]
        )[0]

        metadatas = observation_results.get(
            "metadatas", [[]]
        )[0]

        distances = observation_results.get(
            "distances", [[]]
        )[0]

        hybrid_scores = observation_results.get(
            "hybrid_scores", [[]]
        )[0]

        observations = []

        for i in range(len(documents)):

            observations.append({
                "document": documents[i],
                "metadata": metadatas[i],
                "distance": distances[i],
                "hybrid_score": (
                    hybrid_scores[i]
                    if i < len(hybrid_scores)
                    else None
                )
            })

        # --------------------------------
        # Find unique documents
        # --------------------------------

        document_ids = []

        for observation in observations:

            document_id = (
                observation["metadata"]
                .get("document_id")
            )

            if (
                document_id
                and document_id not in document_ids
            ):
                document_ids.append(document_id)

        # --------------------------------
        # Retrieve complete documents
        # --------------------------------

        full_documents = []

        for document_id in document_ids:

            document = (
                self.document_store.get_document(
                    document_id
                )
            )

            if document:
                full_documents.append(document)

        return {
            "query": query,
            "observations": observations,
            "documents": full_documents
        }