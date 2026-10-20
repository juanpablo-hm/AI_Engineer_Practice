"""Reporte de llamadas al LLM a partir de logs/llm_calls.jsonl.

Uso:
    uv run scripts/report.py [ruta/al/archivo.jsonl]
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

DEFAULT_PATH = Path("logs/llm_calls.jsonl")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else DEFAULT_PATH

    if not path.exists():
        print(f"{path} doesn't exists! Do at least one call")
        return 1

    lines = path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]
    if not events:
        print(f"{events} is empty")
        return 1
    print(f"Llamadas registradas: {len(events)}")

    #   - costo total en USD,
    costo_total = 0
    for event in events:
        costo_total += event.get("cost_usd", 0)
    print(f"Costo total: ${costo_total:.6f} USD")
    #   - latencia p50 y p95 (solo llamadas exitosas; usa statistics.quantiles),
    latencias = []
    for event in events:
        if event.get("success", False):
            latencias.append(event["latency_ms"])

    if not latencias:
        print("Latencia (exitosas): sin llamadas exitosas")
    else:
        cortes = statistics.quantiles(latencias, n=100)
        p50 = cortes[49]
        p95 = cortes[94]
        print(f"Latencia (exitosas): p50 {p50:.0f} ms · p95 {p95:.0f} ms")

    #   - % de llamadas con fallback,
    fallbacks_count = 0
    for event in events:
        if event.get("fallback", False):
            fallbacks_count += 1
    fallback_percent = fallbacks_count / len(events) * 100
    print(f"Porcentaje de llamadas con fallback: {fallback_percent:.1f}%")
    #   - número de llamadas por proveedor.
    proveedores = []
    for event in events:
        proveedores.append(event["provider"])

    numero_provedores = Counter(proveedores)
    print("Llamadas por proveedor")
    for proveedor, cantidad in numero_provedores.most_common():
        print(f" - {proveedor}: {cantidad}")

    # Usa solo la librería estándar y maneja con un mensaje el caso de que el archivo
    # no exista o esté vacío.
    return 0


if __name__ == "__main__":
    sys.exit(main())
