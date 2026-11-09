
# # from app.embeddings.embedder import MedicalEmbedder

# # from app.retrieval.rag_retriever import RAGRetriever
# # from app.knowledge.knowledge_retriever import (
# #     MedicalKnowledgeRetriever
# # )


# # class CombinedRetriever:
# #     """
# #     Retrieves both patient-specific medical records
# #     and general medical knowledge.

# #     A single BGE-M3 embedder is shared by both
# #     retrieval systems.
# #     """

# #     def __init__(
# #         self,
# #         patient_top_k=5,
# #         knowledge_top_k=5
# #     ):

# #         # --------------------------------
# #         # SHARED EMBEDDING MODEL
# #         # --------------------------------
# #         #
# #         # BGE-M3 is loaded ONLY ONCE.
# #         #
# #         shared_embedder = MedicalEmbedder()

# #         # --------------------------------
# #         # PATIENT RAG
# #         # --------------------------------

# #         self.patient_retriever = (
# #             RAGRetriever(
# #                 observation_top_k=patient_top_k,
# #                 embedder=shared_embedder
# #             )
# #         )

# #         # --------------------------------
# #         # MEDICAL KNOWLEDGE RAG
# #         # --------------------------------

# #         self.knowledge_retriever = (
# #             MedicalKnowledgeRetriever(
# #                 top_k=knowledge_top_k,
# #                 embedder=shared_embedder
# #             )
# #         )

# #     def retrieve(
# #         self,
# #         query: str
# #     ):
# #         """
# #         Retrieve patient records and
# #         medical knowledge for the same query.
# #         """

# #         query = query.strip()

# #         if not query:

# #             return {
# #                 "query": query,

# #                 "patient": {
# #                     "observations": [],
# #                     "documents": []
# #                 },

# #                 "knowledge": []
# #             }

# #         # --------------------------------
# #         # PATIENT RAG
# #         # --------------------------------

# #         patient_result = (
# #             self.patient_retriever.retrieve(
# #                 query
# #             )
# #         )

# #         # --------------------------------
# #         # MEDICAL KNOWLEDGE RAG
# #         # --------------------------------

# #         knowledge_result = (
# #             self.knowledge_retriever.retrieve(
# #                 query
# #             )
# #         )

# #         # --------------------------------
# #         # COMBINED RESULT
# #         # --------------------------------

# #         return {
# #             "query": query,

# #             "patient": {
# #                 "observations": (
# #                     patient_result.get(
# #                         "observations",
# #                         []
# #                     )
# #                 ),

# #                 "documents": (
# #                     patient_result.get(
# #                         "documents",
# #                         []
# #                     )
# #                 )
# #             },

# #             "knowledge": knowledge_result
# #         }








# # from app.embeddings.embedder import MedicalEmbedder

# # from app.retrieval.rag_retriever import RAGRetriever
# # from app.knowledge.knowledge_retriever import (
# #     MedicalKnowledgeRetriever
# # )


# # class CombinedRetriever:
# #     """
# #     Retrieves both patient-specific medical records
# #     and general medical knowledge.

# #     A single BGE-M3 embedder is shared by both
# #     retrieval systems.
# #     """

# #     def __init__(
# #         self,
# #         patient_top_k=5,
# #         knowledge_top_k=5
# #     ):

# #         # --------------------------------
# #         # SHARED EMBEDDING MODEL
# #         # --------------------------------

# #         shared_embedder = MedicalEmbedder()

# #         # --------------------------------
# #         # PATIENT RAG
# #         # --------------------------------

# #         self.patient_retriever = RAGRetriever(
# #             observation_top_k=patient_top_k,
# #             embedder=shared_embedder
# #         )

# #         # --------------------------------
# #         # MEDICAL KNOWLEDGE RAG
# #         # --------------------------------

# #         self.knowledge_retriever = (
# #             MedicalKnowledgeRetriever(
# #                 top_k=knowledge_top_k,
# #                 embedder=shared_embedder
# #             )
# #         )

# #     def retrieve(
# #         self,
# #         query: str,
# #         comprehensive: bool = False,
# #         document_ids: list[str] | None = None
# #     ):
# #         """
# #         Retrieve patient records and
# #         medical knowledge for the same query.

# #         comprehensive=False:
# #             Retrieve only the most relevant
# #             patient observations.

# #         comprehensive=True:
# #             Retrieve all patient observations.

# #         document_ids:
# #             Restrict patient-record retrieval to this set of
# #             document_ids (e.g. the current patient's own
# #             analyzed reports). None means "search everything",
# #             which should only be used for internal/debug tools,
# #             never for a real patient-facing request.
# #         """

# #         query = query.strip()

# #         if not query:

# #             return {
# #                 "query": query,

# #                 "patient": {
# #                     "observations": [],
# #                     "documents": []
# #                 },

# #                 "knowledge": []
# #             }

# #         # --------------------------------
# #         # PATIENT RAG
# #         # --------------------------------

# #         patient_result = (
# #             self.patient_retriever.retrieve(
# #                 query,
# #                 comprehensive=comprehensive,
# #                 document_ids=document_ids
# #             )
# #         )

# #         # --------------------------------
# #         # MEDICAL KNOWLEDGE RAG
# #         # --------------------------------

# #         knowledge_result = (
# #             self.knowledge_retriever.retrieve(
# #                 query
# #             )
# #         )

# #         # --------------------------------
# #         # COMBINED RESULT
# #         # --------------------------------

# #         return {
# #             "query": query,

# #             "patient": {
# #                 "observations": (
# #                     patient_result.get(
# #                         "observations",
# #                         []
# #                     )
# #                 ),

# #                 "documents": (
# #                     patient_result.get(
# #                         "documents",
# #                         []
# #                     )
# #                 )
# #             },

# #             "knowledge": knowledge_result
# #         }









# from app.embeddings.embedder import medical_embedder

# from app.retrieval.rag_retriever import RAGRetriever
# from app.knowledge.knowledge_retriever import (
#     MedicalKnowledgeRetriever
# )


# class CombinedRetriever:
#     """
#     Retrieves both patient-specific medical records
#     and general medical knowledge.

#     A single BGE-M3 embedder is shared by both
#     retrieval systems.
#     """

#     def __init__(
#         self,
#         patient_top_k=5,
#         knowledge_top_k=5
#     ):

#         # --------------------------------
#         # SHARED EMBEDDING MODEL
#         # --------------------------------

#         shared_embedder = medical_embedder

#         # --------------------------------
#         # PATIENT RAG
#         # --------------------------------

#         self.patient_retriever = RAGRetriever(
#             observation_top_k=patient_top_k,
#             embedder=shared_embedder
#         )

#         # --------------------------------
#         # MEDICAL KNOWLEDGE RAG
#         # --------------------------------

#         self.knowledge_retriever = MedicalKnowledgeRetriever(
#             top_k=knowledge_top_k,
#             embedder=shared_embedder
#         )






from app.embeddings.embedder import medical_embedder

from app.retrieval.rag_retriever import RAGRetriever
from app.knowledge.knowledge_retriever import (
    MedicalKnowledgeRetriever
)


class CombinedRetriever:
    """
    Retrieves both:

    1. Patient-specific medical records
    2. General medical knowledge

    A single BGE-M3 embedding model is shared
    between both retrieval systems.
    """

    def __init__(
        self,
        patient_top_k: int = 5,
        knowledge_top_k: int = 5
    ):
        """
        Initialize both patient and medical-knowledge
        retrievers using the shared embedding model.

        The embedding model is created once in
        app.embeddings.embedder and reused here.
        """

        # --------------------------------
        # SHARED EMBEDDING MODEL
        # --------------------------------

        shared_embedder = medical_embedder

        # --------------------------------
        # PATIENT RAG
        # --------------------------------

        self.patient_retriever = RAGRetriever(
            observation_top_k=patient_top_k,
            embedder=shared_embedder
        )

        # --------------------------------
        # MEDICAL KNOWLEDGE RAG
        # --------------------------------

        self.knowledge_retriever = MedicalKnowledgeRetriever(
            top_k=knowledge_top_k,
            embedder=shared_embedder
        )

    def retrieve(
        self,
        query: str,
        comprehensive: bool = False,
        document_ids: list[str] | None = None
    ):
        """
        Retrieve patient-specific information and
        general medical knowledge for the same query.

        Args:
            query:
                User's medical query.

            comprehensive:
                If True, retrieve comprehensive patient
                observations instead of only the most
                relevant observations.

            document_ids:
                Optional list of document IDs used to
                restrict patient retrieval.

                For patient-facing requests, this should
                normally contain only the current patient's
                own analyzed report/document IDs.

                None means no document restriction.

        Returns:
            Combined retrieval result containing:

            {
                "query": str,
                "patient": {
                    "observations": list,
                    "documents": list
                },
                "knowledge": ...
            }
        """

        # --------------------------------
        # VALIDATE QUERY
        # --------------------------------

        query = query.strip()

        if not query:
            return {
                "query": query,
                "patient": {
                    "observations": [],
                    "documents": []
                },
                "knowledge": []
            }

        # --------------------------------
        # PATIENT RAG
        # --------------------------------

        patient_result = self.patient_retriever.retrieve(
            query,
            comprehensive=comprehensive,
            document_ids=document_ids
        )

        # --------------------------------
        # MEDICAL KNOWLEDGE RAG
        # --------------------------------

        knowledge_result = self.knowledge_retriever.retrieve(
            query
        )

        # --------------------------------
        # COMBINED RESULT
        # --------------------------------

        return {
            "query": query,

            "patient": {
                "observations": patient_result.get(
                    "observations",
                    []
                ),

                "documents": patient_result.get(
                    "documents",
                    []
                )
            },

            "knowledge": knowledge_result
        }