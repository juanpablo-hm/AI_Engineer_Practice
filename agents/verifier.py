"""Verificador: revisa que cada dato de la respuesta aparezca en las observaciones"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

from agents.react_agent import COMPANY, PROMPTS_DIR, format_observation
from contracts.structured_output import generate_structured
from prompting import PromptKit

if TYPE_CHECKING:
    from agents.trace import TraceStep
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


@dataclass(frozen=True)
class VerifiedAnswer:
    respuesta: str
    verificacion: Verification
    corregida: bool


def _observaciones(traza: list[TraceStep]) -> str:
    if not traza:
        return "(el agente no usó herramientas)"
    textos = []
    for n, step in enumerate(traza, start=1):
        textos.append(
            f"{n} {step.paso.herramienta} {step.paso.argumentos_json or '{}'} -> "
            f"{format_observation(step.observacion)}"
        )
    return "\n".join(textos)


def _verify(client: LLMClient, pregunta: str, respuesta: str, observaciones: str) -> Verification:
    prompt = PromptKit(PROMPTS_DIR).get("verifier")
    messages = prompt.render(
        company=COMPANY,
        pregunta=pregunta,
        respuesta=respuesta,
        observaciones=observaciones,
    )
    log_extra = {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
    }
    return generate_structured(
        client, messages, Verification, log_extra=log_extra, **prompt.model_params
    )


def verify_and_revise(
    client: LLMClient, pregunta: str, respuesta: str, traza: list[TraceStep]
) -> VerifiedAnswer:
    observaciones = _observaciones(traza)
    verificacion = _verify(client, pregunta, respuesta, observaciones)
    if verificacion.aprobada:
        return VerifiedAnswer(respuesta, verificacion, corregida=False)

    reviser = PromptKit(PROMPTS_DIR).get("reviser")
    messages = reviser.render(
        company=COMPANY,
        pregunta=pregunta,
        respuesta=respuesta,
        observaciones=observaciones,
        problemas=verificacion.problemas,
    )
    corregida = client.generate(
        messages,
        log_extra={
            "prompt_name": reviser.name,
            "prompt_version": reviser.version,
        },
        **reviser.model_params,
    ).text.strip()

    verificacion = _verify(client, pregunta, corregida, observaciones)
    return VerifiedAnswer(corregida, verificacion, corregida=True)
