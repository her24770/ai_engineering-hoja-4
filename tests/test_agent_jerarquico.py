"""Pruebas unitarias para la arquitectura multiagente jerárquica."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Configurar sys.path para importar desde agent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from agent_jerarquico import create_hierarchical_agents


def _tool_names(agent) -> list[str]:
    """Helper para extraer los nombres de las tools configuradas en un agente."""
    return [getattr(t, "name", str(t)) for t in agent.tools]


def test_faq_worker_configuration():
    """1. Verifica que FAQ Worker (nivel 3) tenga únicamente search_faq y no check_weather."""
    _, _, _, faq_agent, weather_agent = create_hierarchical_agents()

    assert faq_agent.name == "FAQ Worker"
    tool_names = _tool_names(faq_agent)
    assert "search_faq" in tool_names, "FAQ Worker debe tener asignada search_faq"
    assert "check_weather" not in tool_names, "FAQ Worker no debe tener asignada check_weather"
    assert len(faq_agent.tools) == 1


def test_weather_worker_configuration():
    """2. Verifica que Weather Worker (nivel 3) tenga únicamente check_weather y no search_faq."""
    _, _, _, faq_agent, weather_agent = create_hierarchical_agents()

    assert weather_agent.name == "Weather and Scheduling Worker"
    tool_names = _tool_names(weather_agent)
    assert "check_weather" in tool_names, "Weather Worker debe tener asignada check_weather"
    assert "search_faq" not in tool_names, "Weather Worker no debe tener asignada search_faq"
    assert len(weather_agent.tools) == 1


def _is_agent_as_tool(tool) -> bool:
    """Las tools creadas con Agent.as_tool() usan el schema genérico 'AgentAsToolInput' (campo 'input'),
    a diferencia de las tools de negocio (function_tool) que exponen los parámetros reales de la función."""
    schema = getattr(tool, "params_json_schema", {}) or {}
    return schema.get("title") == "AgentAsToolInput"


def test_customer_service_manager_configuration():
    """3. Verifica que el Customer Service Manager (nivel 2) solo delegue al FAQ Worker."""
    _, customer_service_manager, _, _, _ = create_hierarchical_agents()

    assert customer_service_manager.name == "Customer Service Manager"
    assert len(customer_service_manager.tools) == 1, "El manager de atención al cliente debe exponer una única tool"

    tool = customer_service_manager.tools[0]
    assert tool.name == "faq_worker"
    assert _is_agent_as_tool(tool), "La tool del manager debe ser un wrapper as_tool() del FAQ Worker"


def test_operations_manager_configuration():
    """4. Verifica que el Operations Manager (nivel 2) solo delegue al Weather Worker."""
    _, _, operations_manager, _, _ = create_hierarchical_agents()

    assert operations_manager.name == "Operations Manager"
    assert len(operations_manager.tools) == 1, "El manager de operaciones debe exponer una única tool"

    tool = operations_manager.tools[0]
    assert tool.name == "weather_worker"
    assert _is_agent_as_tool(tool), "La tool del manager debe ser un wrapper as_tool() del Weather Worker"


def test_director_agent_configuration():
    """5. Verifica que Director Agent (nivel 1) solo conozca a los dos managers, no a los workers directamente."""
    director_agent, _, _, _, _ = create_hierarchical_agents()

    assert director_agent.name == "Director Agent"
    tool_names = _tool_names(director_agent)
    assert set(tool_names) == {"customer_service_manager", "operations_manager"}
    assert len(director_agent.tools) == 2

    # El Director no debe tener acceso directo a las tools de negocio (search_faq / check_weather)
    assert "search_faq" not in tool_names
    assert "check_weather" not in tool_names

    for tool in director_agent.tools:
        assert _is_agent_as_tool(tool), f"La tool '{tool.name}' del Director debe ser un wrapper as_tool()"


def test_hierarchy_uses_as_tool_at_every_level():
    """6. Verifica que la jerarquía completa (3 niveles) esté construida con as_tool(), no con handoffs."""
    director_agent, customer_service_manager, operations_manager, faq_agent, weather_agent = create_hierarchical_agents()

    # Nivel 1 -> Nivel 2: el Director delega en los managers vía as_tool()
    for tool in director_agent.tools:
        assert _is_agent_as_tool(tool), "El Director debe delegar en los managers mediante as_tool()"

    # Nivel 2 -> Nivel 3: cada manager delega en su worker vía as_tool()
    for manager in [customer_service_manager, operations_manager]:
        for tool in manager.tools:
            assert _is_agent_as_tool(tool), f"{manager.name} debe delegar en su worker mediante as_tool()"

    # Los workers de base sí deben usar sus tools de negocio, no as_tool()
    for worker in [faq_agent, weather_agent]:
        for tool in worker.tools:
            assert not _is_agent_as_tool(tool), f"{worker.name} debe usar tools de negocio, no as_tool()"

    # Ningún agente de la jerarquía debe usar handoffs (mecanismo de la arquitectura descentralizada)
    for agent in [director_agent, customer_service_manager, operations_manager, faq_agent, weather_agent]:
        assert not getattr(agent, "handoffs", []), f"{agent.name} no debe usar handoffs en la arquitectura jerárquica"


def test_three_levels_are_distinct_agents():
    """7. Verifica que existan exactamente 5 agentes distintos organizados en 3 niveles."""
    director_agent, customer_service_manager, operations_manager, faq_agent, weather_agent = create_hierarchical_agents()

    names = [a.name for a in [director_agent, customer_service_manager, operations_manager, faq_agent, weather_agent]]
    assert len(set(names)) == 5, "Los 5 agentes de la jerarquía deben tener nombres únicos"


def test_main_interactive_loop(monkeypatch, capsys):
    """8. Prueba el ciclo de ejecución interactivo de main() con mock de runner e inputs."""
    from unittest.mock import patch
    import agent_jerarquico

    monkeypatch.setenv("OPENAI_API_KEY", "mock-key-for-test")

    mock_result = MagicMock()
    mock_result.final_output = "Respuesta de prueba sobre Parachute S.A."

    with patch("agent_jerarquico.get_embedding_model"), \
         patch("agent_jerarquico.Runner") as mock_runner_cls, \
         patch("builtins.input", side_effect=["¿Tienen saltos tandem?", "Bye"]):

        mock_runner = MagicMock()
        mock_runner.run_sync.return_value = mock_result
        mock_runner_cls.return_value = mock_runner

        agent_jerarquico.main()

    captured = capsys.readouterr().out
    assert "Arquitectura Jerárquica Inicializada" in captured
    assert "Director/Respuesta Final: Respuesta de prueba sobre Parachute S.A." in captured
    assert "Hasta luego." in captured


def test_main_exits_without_api_key(monkeypatch):
    """9. Verifica que main() finalice si no hay OPENAI_API_KEY configurada."""
    from unittest.mock import patch
    import agent_jerarquico

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Evitar que load_dotenv() vuelva a poblar OPENAI_API_KEY desde el .env real del entorno
    with patch("agent_jerarquico.load_dotenv"):
        with pytest.raises(SystemExit):
            agent_jerarquico.main()
