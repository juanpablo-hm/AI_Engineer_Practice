"""Verificador: revisa que cada dato de la respuesta aparezca en las observaciones"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from agents.react_agent import format_observation
from contracts.structured_output import generate_structured
from prompting import PromptKit

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
COMPANY = "Acme Operaciones"

if TYPE_CHECKING:
    from agents.trace import AgentResult, TraceStep
    from core.llm_client import LLMClient


class Verification(BaseModel):
    problemas: list[str] = Field(
        description="Cada dato de la respuesta que no aparece en las observaciones; "
        "vacía si todo coincide; Si hay un problema, "
        "indica qué dice la respuesta y qué dice la observación"
    )
    aprobada: bool = Field(description="true solo si problemas está vacía")

    @model_validator(mode="after")
    def _consistente(self) -> Verification:
        if self.aprobada == bool(self.problemas):
            raise ValueError(
                "aprobada debe ser true si problemas está vacía y false si tiene elementos."
            )
        return self


def _observaciones(traza: list[TraceStep]) -> str:
    textos = []
    for n, paso in enumerate(traza, start=1):
        textos.append(f"{n} {format_observation(paso.observacion)}")
    return "\n".join(textos)


def verify(client: LLMClient, pregunta: str, resultado: AgentResult) -> Verification:
    prompt = PromptKit(PROMPTS_DIR).get("verifier")
    messages = prompt.render(
        company=COMPANY,
        pregunta=pregunta,
        respuesta=resultado.respuesta,
        observaciones=_observaciones(resultado.traza),
    )
    log_extra = {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
    }
    return generate_structured(
        client, messages, Verification, log_extra=log_extra, **prompt.model_params
    )


def revise(
    client: LLMClient, pregunta: str, resultado: AgentResult, verificacion: Verification
) -> str:
    prompt = PromptKit(PROMPTS_DIR).get("reviser")
    messages = prompt.render(
        company=COMPANY,
        pregunta=pregunta,
        respuesta=resultado.respuesta,
        observaciones=_observaciones(resultado.traza),
        problemas=verificacion.problemas,
    )
    log_extra = {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
    }

    return client.generate(messages, log_extra=log_extra, **prompt.model_params).text
