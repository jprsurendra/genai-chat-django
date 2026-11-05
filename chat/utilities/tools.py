import ast
import operator
import logging
import re
from django.conf import settings
from tavily import TavilyClient

logger = logging.getLogger(__name__)

# Safe operators for the calculator
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    """
    Safely evaluates a mathematical expression.
    Includes a limit on exponentiation to prevent CPU/Memory DoS attacks (e.g., 9**9**9).
    """
    try:
        expression = expression.replace('^', '**')
        node = ast.parse(expression, mode='eval').body

        def _eval(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                # 🔥 SECURITY FIX (H2): Prevent DoS via huge exponents
                if isinstance(node.op, ast.Pow):
                    left = _eval(node.left)
                    right = _eval(node.right)
                    # Limit the exponent and base to avoid freezing the CPU
                    if abs(right) > 10 or abs(left) > 10000:
                        raise ValueError("Exponent too large. Please use smaller numbers.")
                    return operator.pow(left, right)
                return OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return OPERATORS[type(node.op)](_eval(node.operand))
            else:
                raise TypeError(f"Unsupported operation: {type(node)}")

        result = _eval(node)
        return str(result)
    except Exception as e:
        logger.error(f"Calculator error for '{expression}': {e}")
        return f"Error: Could not calculate '{expression}'"


# 🔥 NEW: Web Search Tool
def web_search(query: str) -> str:
    """
    Searches the web for real-time information using Tavily.
    Returns a summarized text of the top results.
    """
    try:
        # Initialize the Tavily client with the API key from settings
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        # Perform the search (search_depth="basic" is faster)
        response = tavily_client.search(query=query, search_depth="basic", max_results=3)

        # Extract and combine the results
        results = response.get("results", [])
        if not results:
            return "No results found on the web."

        formatted_results = []
        for res in results:
            content = res.get('content', '')
            # 🔥 SECURITY FIX (H4): Check for simple prompt injection patterns
            injection_keywords = ["ignore previous instructions", "system prompt", "you are now"]
            if any(keyword in content.lower() for keyword in injection_keywords):
                logger.warning(f"Skipped a search result due to potential prompt injection.")
                continue

            formatted_results.append(f"Source: {res.get('url')}\nContent: {content}")

        if not formatted_results:
            return "No safe results found on the web."

        # 🔥 SECURITY FIX (H4): Wrap the entire result in an untrusted block
        return "<untrusted_web_data>\n" + "\n\n".join(formatted_results) + "\n</untrusted_web_data>"

    except Exception as e:
        logger.error(f"Web search error for '{query}': {e}")
        return f"Error: Could not search the web for '{query}'"