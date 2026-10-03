"""Asserts de Python reutilizables para los test cases de promptfoo.

Uso en un test case (faq_tests.yaml / citas_tests.yaml):

    - vars:
        inquiry: "..."
        expected_tool: "faq_worker"   # o "weather_worker"
      assert:
        - type: python
          value: "file://asserts.py:used_tool"
"""


def used_tool(output: str, context: dict):
    """Verifica que el Manager haya invocado la tool esperada (tool execution).

    Requiere que el test case defina `vars.expected_tool` con el nombre exacto
    del worker (ej. "faq_worker" o "weather_worker"). La lista de tools
    realmente invocadas viene en context['metadata']['tool_names'], que llena
    provider.py a partir de run_query().
    """
    test_vars = context.get("vars", {}) or {}
    metadata = context.get("metadata", {}) or {}

    expected_tool = test_vars.get("expected_tool")
    tool_names = metadata.get("tool_names", [])

    if not expected_tool:
        return {
            "pass": False,
            "score": 0.0,
            "reason": "El test case no definió vars.expected_tool",
        }

    passed = expected_tool in tool_names
    return {
        "pass": passed,
        "score": 1.0 if passed else 0.0,
        "reason": (
            f"'{expected_tool}' fue invocada correctamente"
            if passed
            else f"Se esperaba '{expected_tool}' pero se llamó: {tool_names}"
        ),
    }
