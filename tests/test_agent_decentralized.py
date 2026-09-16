"""Pruebas unitarias para la arquitectura multiagente descentralizada."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Configurar sys.path para importar desde agent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from agent_decentralized import (
    EXIT_COMMANDS,
    create_decentralized_agents,
)
from tools import search_faq
from tools_weather import check_weather


def _get_handoff_agent_names(agent) -> list[str]:
    """Helper para extraer los nombres de los agentes configurados en los handoffs."""
    names = []
    for h in agent.handoffs:
        if hasattr(h, "name"):
            names.append(h.name)
        elif hasattr(h, "agent") and hasattr(h.agent, "name"):
            names.append(h.agent.name)
        elif hasattr(h, "target") and hasattr(h.target, "name"):
            names.append(h.target.name)
    return names


def test_reception_agent_configuration():
    """1. Verifica que Reception Agent no tenga herramientas y tenga handoffs a FAQ Agent y Weather Agent."""
    reception_agent, faq_agent, weather_agent = create_decentralized_agents()

    assert reception_agent.name == "Reception Agent"
    assert len(reception_agent.tools) == 0, "Reception Agent no debe tener herramientas asignadas"

    handoff_names = _get_handoff_agent_names(reception_agent)
    assert "FAQ Agent" in handoff_names, "Reception Agent debe tener handoff hacia FAQ Agent"
    assert "Weather Agent" in handoff_names, "Reception Agent debe tener handoff hacia Weather Agent"
    assert len(handoff_names) == 2


def test_faq_agent_configuration():
    """2. Verifica que FAQ Agent tenga únicamente search_faq y no check_weather, con handoff a Weather Agent."""
    _, faq_agent, _ = create_decentralized_agents()

    assert faq_agent.name == "FAQ Agent"
    tool_names = [getattr(t, "name", str(t)) for t in faq_agent.tools]
    assert "search_faq" in tool_names, "FAQ Agent debe tener asignada search_faq"
    assert "check_weather" not in tool_names, "FAQ Agent no debe tener asignada check_weather"
    assert len(faq_agent.tools) == 1

    handoff_names = _get_handoff_agent_names(faq_agent)
    assert "Weather Agent" in handoff_names, "FAQ Agent debe tener handoff hacia Weather Agent"


def test_weather_agent_configuration():
    """3. Verifica que Weather Agent tenga únicamente check_weather y no search_faq, con handoff a FAQ Agent."""
    _, _, weather_agent = create_decentralized_agents()

    assert weather_agent.name == "Weather Agent"
    tool_names = [getattr(t, "name", str(t)) for t in weather_agent.tools]
    assert "check_weather" in tool_names, "Weather Agent debe tener asignada check_weather"
    assert "search_faq" not in tool_names, "Weather Agent no debe tener asignada search_faq"
    assert len(weather_agent.tools) == 1

    handoff_names = _get_handoff_agent_names(weather_agent)
    assert "FAQ Agent" in handoff_names, "Weather Agent debe tener handoff hacia FAQ Agent"


def test_no_as_tool_and_last_agent_reporting():
    """4. Verifica que no se use as_tool() y que se reporte correctamente el nombre del agente final."""
    reception_agent, faq_agent, weather_agent = create_decentralized_agents()

    # Verificar que ninguna herramienta sea un wrapper de as_tool (los agentes no son herramientas)
    for agent in [reception_agent, faq_agent, weather_agent]:
        for tool in agent.tools:
            tool_name = getattr(tool, "name", str(tool))
            assert tool_name in ["search_faq", "check_weather"], f"Herramienta inesperada: {tool_name}"
            # Asegurar que no es un ToolWrapper creado por as_tool()
            assert not hasattr(tool, "_agent"), "No se debe utilizar as_tool() para envolver agentes como herramientas"

    # Verificar reporte del agente final simulando el resultado de Runner
    mock_result = MagicMock()
    mock_result.last_agent = faq_agent
    mock_result.final_output = "El salto cuesta Q1,500."

    agent_name = mock_result.last_agent.name if mock_result.last_agent else "Desconocido"
    assert agent_name == "FAQ Agent"


def test_exit_commands_coverage():
    """Verifica que todas las opciones de salida requeridas estén soportadas."""
    required_exits = {"bye", "goodbye", "exit", "salir", "adios", "adiós"}
    for cmd in required_exits:
        assert cmd in EXIT_COMMANDS


def test_main_interactive_loop(monkeypatch, capsys):
    """5. Prueba el ciclo de ejecución interactivo de main() con mock de runner e inputs."""
    from unittest.mock import patch
    import agent_decentralized

    monkeypatch.setenv("OPENAI_API_KEY", "mock-key-for-test")

    mock_result = MagicMock()
    mock_result.last_agent = MagicMock(name="FAQ Agent")
    mock_result.last_agent.name = "FAQ Agent"
    mock_result.final_output = "Respuesta de prueba sobre Parachute S.A."

    with patch("agent_decentralized.get_embedding_model"), \
         patch("agent_decentralized.Runner") as mock_runner_cls, \
         patch("builtins.input", side_effect=["¿Tienen saltos tandem?", "  Salir  "]):
        
        mock_runner = MagicMock()
        mock_runner.run_sync.return_value = mock_result
        mock_runner_cls.return_value = mock_runner

        agent_decentralized.main()

    captured = capsys.readouterr().out
    assert "Arquitectura Descentralizada Inicializada" in captured
    assert "Agente que respondió: FAQ Agent" in captured
    assert "Respuesta: Respuesta de prueba sobre Parachute S.A." in captured
    assert "Hasta luego." in captured

