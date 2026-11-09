class QueryRouter:

    def route(self, query: str) -> dict:

        query = query.strip().lower()

        if not query:
            return {
                "scope": "specific"
            }

        # --------------------------------------------------
        # COMPREHENSIVE QUERY PATTERNS
        # --------------------------------------------------

        comprehensive_patterns = [

            # All / entire records
            "all my",
            "all of my",
            "all results",
            "all tests",
            "all blood tests",
            "all my tests",
            "all my results",
            "all my values",
            "all my labs",

            # Abnormality questions
            "any abnormal",
            "any abnormalities",
            "any abnormal results",
            "any abnormal tests",
            "any abnormal values",
            "any abnormal findings",
            "abnormal results",
            "abnormal tests",
            "abnormal values",
            "abnormal findings",

            "outside the range",
            "outside reference",
            "outside normal",
            "outside the reference range",
            "outside normal range",
            "outside their reference range",

            # Which / what results
            "which results",
            "which tests",
            "which values",
            "which of my tests",
            "which of my results",
            "which of my values",
            "which of my labs",

            "which tests are abnormal",
            "which results are abnormal",
            "which values are abnormal",
            "which of my tests are abnormal",
            "which of my results are abnormal",
            "which of my values are abnormal",

            "what results",
            "what tests",
            "what values",

            # Review entire report
            "review my report",
            "review my reports",
            "review all",
            "review my entire report",
            "review my entire reports",

            "entire report",
            "entire reports",
            "whole report",
            "whole reports",
            "whole blood test",
            "whole blood tests",

            "overall blood work",
            "overall blood tests",
            "overall results",

            # Summary questions
            "overall summary",
            "overall summaries",
            "summary of my results",
            "summary of my tests",
            "summary of my blood tests",
            "summary of my blood work",

            "summarize my results",
            "summarize my tests",
            "summarize my blood tests",
            "summarize my blood work",

            "give me a summary",
            "give me an overall summary",
            "give me a summary of my results",
            "give me a summary of my tests",
            "give me an overall summary of my results",
            "give me an overall summary of my tests",

            # General overview
            "overall health results",
            "overall health summary",
            "overall report",
            "overall test results",
            "overall blood test results",
            "overview of my results",
            "overview of my tests",
            "overview of my blood tests"
        ]

        # --------------------------------------------------
        # CHECK COMPREHENSIVE PATTERNS
        # --------------------------------------------------

        for pattern in comprehensive_patterns:

            if pattern in query:

                return {
                    "scope": "comprehensive"
                }

        # --------------------------------------------------
        # DEFAULT
        # --------------------------------------------------

        return {
            "scope": "specific"
        }