"""
Helps you pick MIN_RERANK_SCORE (src/config.py), the cutoff below which the agent
says "the knowledge base doesn't cover this" without calling the LLM.

It prints the best reranker score for questions the KB should answer and for
questions it shouldn't (in both languages), then suggests a cutoff between the
two groups. Doesn't need Ollama.

    python check_retrieval.py
    docker compose exec backend python check_retrieval.py
"""
from src import config
from src.agent import CodeReviewAgent

ANSWERABLE = {
    "python": [
        "What is SQL injection and how can it be prevented in Python?",
        "Why is string concatenation in a loop slow, and what should I use instead?",
        "What is the Single Responsibility Principle and how does it apply to Python functions?",
        "How should I handle hardcoded API keys and passwords in Python code?",
        "What is the AAA pattern in unit testing?",
        "What is the lru_cache decorator and when should I use it?",
        "What HTTP status code should be returned when a resource is not found?",
        "How should I structure error handling AND logging in a production Python service?",
        "What is the N+1 query problem and how do I fix it with SQLAlchemy?",
        "How do I prevent path traversal?",
    ],
    "csharp": [
        "How do I prevent SQL injection with Entity Framework Core?",
        "Why should I avoid async void in C#?",
        "Why does calling .Result on a Task cause deadlocks?",
        "Should I create a new HttpClient for every request?",
        "How do I use ILogger with structured logging?",
        "What is the difference between Scoped, Transient and Singleton services?",
        "How do I write parameterized tests in xUnit?",
        "How do I enable nullable reference types?",
        "How do I add retries and a circuit breaker with Polly?",
        "How do I return ProblemDetails from an ASP.NET Core API?",
    ],
}
UNANSWERABLE = [
    "What is the best JavaScript framework to use in 2025?",
    "How do I train a neural network in PyTorch for image classification?",
    "What is the speed of light?",
    "How do I deploy a Kubernetes cluster on AWS?",
    "Write me a recipe for chocolate cake.",
    "What are the current interest rates set by the Federal Reserve?",
]


def main():
    agent = CodeReviewAgent.from_knowledge_base()

    def best(question: str, language: str) -> tuple[float, str]:
        passages, _ = agent._retrieve([question], language)      # same retrieval the agent uses
        return (passages[0].score, passages[0].chunk.chunk_id) if passages else (float("-inf"), "-")

    rows = []
    for language, questions in ANSWERABLE.items():
        rows += [(True, language, q, *best(q, language)) for q in questions]
    for language in ANSWERABLE:
        rows += [(False, language, q, *best(q, language)) for q in UNANSWERABLE]

    print(f"\n{'answer?':<8} {'lang':<7} {'score':>7}  {'top chunk':<40} question")
    print("-" * 110)
    for should, language, q, score, cid in rows:
        wrong = (score >= config.MIN_RERANK_SCORE) != should
        print(f"{'yes' if should else 'no':<8} {language:<7} {score:>7.2f}  {cid:<40} {q[:45]}"
              f"{'   <-- wrong with current cutoff' if wrong else ''}")

    lowest_yes = min(r[3] for r in rows if r[0])
    highest_no = max(r[3] for r in rows if not r[0])
    print(f"\nCurrent MIN_RERANK_SCORE = {config.MIN_RERANK_SCORE}")
    print(f"Lowest 'should answer' score:     {lowest_yes:.2f}")
    print(f"Highest 'shouldn't answer' score: {highest_no:.2f}")
    if lowest_yes > highest_no:
        print(f"-> The groups separate cleanly. Suggested MIN_RERANK_SCORE = {(lowest_yes + highest_no) / 2:.1f}")
    else:
        print("-> The groups overlap. Pick a value that keeps the 'should answer' questions; the LLM's own\n"
              "   abstain rule will still catch most off-topic questions that get past the cutoff.")


if __name__ == "__main__":
    main()
