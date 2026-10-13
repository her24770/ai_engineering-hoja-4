"""Definición del AgentCard y Skills de Parachute S.A. para el protocolo A2A.

Expone el sistema multi-agente centralizado como un solo agente con dos habilidades:
  1. FAQs y Políticas (base de conocimientos en pgvector).
  2. Citas y Factibilidad Meteorológica (condiciones meteorológicas con Open-Meteo).
"""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


def get_agent_card(base_url: str = "http://127.0.0.1:9000") -> AgentCard:
    """Genera el AgentCard oficial de Parachute S.A. con sus metadatos y skills."""
    return AgentCard(
        name="Parachute Customer Service Agent",
        description=(
            "Agente supervisor unificado de atención al cliente de Parachute S.A. "
            "Responde preguntas frecuentes sobre políticas, precios y requisitos de seguridad, "
            "y evalúa la factibilidad meteorológica para realizar saltos en paracaídas en fechas específicas."
        ),
        version="1.0.0",
        documentation_url=f"{base_url}/docs",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
            extended_agent_card=False,
        ),
        supported_interfaces=[
            AgentInterface(
                url=base_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        skills=[
            AgentSkill(
                id="faqs",
                name="FAQs y Políticas de Parachute S.A.",
                description=(
                    "Consulta la base de conocimientos oficial de Parachute S.A. "
                    "Informa sobre restricciones de peso (máximo 100 kg), edad mínima (18 años o 16 con tutor legal), "
                    "precios, recargos administrativos (Q250 entre 90 y 100 kg) y normativas de seguridad para saltos tándem."
                ),
                tags=["faqs", "politicas", "precios", "requisitos", "seguridad", "tándem"],
                examples=[
                    "¿Cuál es el peso máximo permitido para saltar?",
                    "¿Qué edad mínima se requiere para un salto en paracaídas?",
                    "¿Hay cobros o recargos adicionales si peso más de 90 kg?",
                    "¿Dónde están ubicadas sus instalaciones de salto?",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
            AgentSkill(
                id="citas_clima",
                name="Citas y Factibilidad Meteorológica",
                description=(
                    "Evalúa condiciones meteorológicas (viento, visibilidad, precipitación vía Open-Meteo) "
                    "para determinar si una fecha (máximo 16 días a futuro) es APTA, MARGINAL o PROHIBIDA para saltar. "
                    "NOTA: Esta skill únicamente dictamina la viabilidad climática del salto en la fecha indicada; "
                    "no realiza reservas ni inserciones de citas en bases de datos."
                ),
                tags=["clima", "citas", "factibilidad", "meteorologia", "saltos", "fechas"],
                examples=[
                    "¿Puedo saltar este sábado?",
                    "¿Las condiciones son aptas para saltar mañana?",
                    "Quiero agendar un salto para el próximo fin de semana, ¿el clima es bueno?",
                    "¿Se puede saltar el 2026-10-20?",
                ],
                input_modes=["text/plain"],
                output_modes=["text/plain"],
            ),
        ],
    )
