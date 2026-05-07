"""Local stub backend for dev/demo before the teammate's FastAPI is ready.

Matches the guide-spec contract:
  GET  /informes              -> [{id_informe, descripcion_procedimiento, hospital}, ...]
  GET  /informes/{id}         -> full InformeDetail (forward-compat extension)
  POST /procesar/{informe_id} -> {trace, final_text, decision}
  GET  /health                -> {ok: true}

Run:
  python frontend/dev_stub_backend.py
  # then in another terminal:
  cd frontend && streamlit run app.py

This stub is never deployed — it exists only so the frontend can be smoke-
tested end-to-end before the real backend stabilizes.
"""

from __future__ import annotations

import time
from datetime import date, timedelta
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOY = date.today()


def _days_ago(n: int) -> str:
    return (HOY - timedelta(days=n)).isoformat()


def _days_from_now(n: int) -> str:
    return (HOY + timedelta(days=n)).isoformat()


# Synthetic patient fixtures. Cedulas use 0000000001/2/3 (NOT real Ecuadorian
# format) and patient names are explicitly marked [DEMO]. Hospitals use
# generic names that do not resemble real Ecuadorian institutions. This stub
# is dev-only and binds to 127.0.0.1, but defense-in-depth: even if it
# leaked, no real PII is exposed.
INFORMES = {
    "INF-001": {
        "id_informe": "INF-001",
        "paciente_cedula": "0000000001",
        "paciente_nombre": "[DEMO] Paciente Uno",
        "paciente_fecha_nacimiento": "1985-05-12",
        "paciente_sexo": "M",
        "poliza_numero": "POL-001",
        "plan_nombre": "Plan Salud Premium",
        "plan_nivel": "Premium",
        "plan_id": "plan_premium",
        "poliza_fecha_alta": _days_ago(730),
        "poliza_estado": "Vigente",
        "fecha_emision": _days_ago(1),
        "hospital": "Hospital Demo Norte",
        "medico_tratante": "Dr. [DEMO] Uno",
        "diagnostico_cie10": "K35.9",
        "diagnostico_desc": "Apendicitis aguda, no especificada",
        "procedimiento_cpt": "44970",
        "descripcion_procedimiento": "Apendicectomía laparoscópica",
        "justificacion_clinica": (
            "Paciente con dolor abdominal en fosa ilíaca derecha, leucocitosis, "
            "ecografía confirma apendicitis aguda. Indicación quirúrgica urgente."
        ),
        "fecha_programada": _days_from_now(2),
        "urgencia": "Urgente",
        "documentos_adjuntos": ["informe_quirurgico", "examenes_prequirurgicos"],
    },
    "INF-002": {
        "id_informe": "INF-002",
        "paciente_cedula": "0000000002",
        "paciente_nombre": "[DEMO] Paciente Dos",
        "paciente_fecha_nacimiento": "1978-09-03",
        "paciente_sexo": "F",
        "poliza_numero": "POL-002",
        "plan_nombre": "Plan Salud Estándar",
        "plan_nivel": "Estandar",
        "plan_id": "plan_estandar",
        "poliza_fecha_alta": _days_ago(45),
        "poliza_estado": "Vigente",
        "fecha_emision": _days_ago(2),
        "hospital": "Hospital Demo Centro",
        "medico_tratante": "Dra. [DEMO] Dos",
        "diagnostico_cie10": "E66.01",
        "diagnostico_desc": "Obesidad mórbida por exceso de calorías",
        "procedimiento_cpt": "43644",
        "descripcion_procedimiento": "Cirugía bariátrica - bypass gástrico",
        "justificacion_clinica": (
            "Paciente con IMC 41, comorbilidades metabólicas, falla de terapia "
            "conservadora 18 meses. Candidata a manejo quirúrgico."
        ),
        "fecha_programada": _days_from_now(14),
        "urgencia": "Electiva",
        "documentos_adjuntos": [
            "informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"
        ],
    },
    "INF-003": {
        "id_informe": "INF-003",
        "paciente_cedula": "0000000003",
        "paciente_nombre": "[DEMO] Paciente Tres",
        "paciente_fecha_nacimiento": "1990-01-22",
        "paciente_sexo": "M",
        "poliza_numero": "POL-003",
        "plan_nombre": "Plan Salud Estándar",
        "plan_nivel": "Estandar",
        "plan_id": "plan_estandar",
        "poliza_fecha_alta": _days_ago(365),
        "poliza_estado": "Vigente",
        "fecha_emision": _days_ago(1),
        "hospital": "Hospital Demo Sur",
        "medico_tratante": "Dr. [DEMO] Tres",
        "diagnostico_cie10": "K80.20",
        "diagnostico_desc": "Cálculo de la vesícula biliar sin colecistitis",
        "procedimiento_cpt": "47562",
        "descripcion_procedimiento": "Colecistectomía laparoscópica",
        "justificacion_clinica": (
            "Paciente con colelitiasis sintomática, episodios de cólico biliar "
            "recurrentes, ecografía con cálculo de 2cm. Indicación quirúrgica electiva."
        ),
        "fecha_programada": _days_from_now(7),
        "urgencia": "Electiva",
        "documentos_adjuntos": ["informe_quirurgico"],
    },
}


COBERTURAS = {
    ("44970", "plan_premium"):  {"cubierto": True, "dias_carencia": 30,
                                  "documentos_requeridos": ["informe_quirurgico"]},
    ("44970", "plan_estandar"): {"cubierto": True, "dias_carencia": 60,
                                  "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos"]},
    ("47562", "plan_estandar"): {"cubierto": True, "dias_carencia": 90,
                                  "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"]},
    ("47562", "plan_premium"):  {"cubierto": True, "dias_carencia": 30,
                                  "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos"]},
    ("43644", "plan_estandar"): {"cubierto": True, "dias_carencia": 365,
                                  "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos",
                                                              "segundo_dictamen", "exames_imagen"]},
    ("43644", "plan_premium"):  {"cubierto": True, "dias_carencia": 180,
                                  "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos",
                                                              "segundo_dictamen"]},
}


def _trace_for(informe_id: str) -> dict:
    inf = INFORMES[informe_id]
    trace = [
        {"tool": "get_informe_medico", "input": {"informe_id": informe_id},
         "output": {
             "paciente_cedula": inf["paciente_cedula"],
             "procedimiento_cpt": inf["procedimiento_cpt"],
             "fecha_programada": inf["fecha_programada"],
             "documentos_adjuntos": inf["documentos_adjuntos"],
         }},
        {"tool": "get_poliza_paciente", "input": {"cedula": inf["paciente_cedula"]},
         "output": {
             "numero": inf["poliza_numero"],
             "plan_id": "plan_" + inf["plan_nivel"].lower(),
             "plan_nombre": inf["plan_nombre"],
             "fecha_alta": inf["poliza_fecha_alta"],
             "estado": inf["poliza_estado"],
         }},
    ]

    if informe_id == "INF-001":
        trace += [
            {"tool": "get_cobertura", "input": {"plan_id": "plan_premium", "codigo_cpt": "44970"},
             "output": {"cubierto": True, "dias_carencia": 30,
                        "documentos_requeridos": ["informe_quirurgico"]}},
            {"tool": "verificar_carencia", "input": {
                "fecha_alta_poliza": inf["poliza_fecha_alta"],
                "fecha_evento": inf["fecha_programada"],
                "dias_carencia_requeridos": 30,
            }, "output": {"cumple": True, "dias_transcurridos": 732, "dias_requeridos": 30,
                          "dias_faltantes": 0}},
            {"tool": "validar_documentos", "input": {
                "documentos_requeridos": ["informe_quirurgico"],
                "documentos_adjuntos": inf["documentos_adjuntos"],
            }, "output": {"completo": True, "documentos_faltantes": []}},
            {"tool": "emitir_decision", "input": {
                "informe_id": "INF-001", "decision": "Aprobado",
            }, "output": {"ok": True, "decision_id": "DEC-INF-001-APR"}},
        ]
        decision = {
            "decision": "Aprobado",
            "justificacion": (
                "Se aprueba la pre-autorización para Apendicectomía laparoscópica (CPT 44970). "
                "Póliza vigente desde hace más de 2 años, cumple carencia de 30 días requeridos. "
                "Todos los documentos requeridos están adjuntos."
            ),
            "clausula_aplicada": "Cláusula 2.1 — Cobertura quirúrgica vigente",
            "documentos_faltantes": [],
        }
    elif informe_id == "INF-002":
        trace += [
            {"tool": "get_cobertura", "input": {"plan_id": "plan_estandar", "codigo_cpt": "43644"},
             "output": {"cubierto": True, "dias_carencia": 365,
                        "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos",
                                                  "segundo_dictamen", "exames_imagen"]}},
            {"tool": "verificar_carencia", "input": {
                "fecha_alta_poliza": inf["poliza_fecha_alta"],
                "fecha_evento": inf["fecha_programada"],
                "dias_carencia_requeridos": 365,
            }, "output": {"cumple": False, "dias_transcurridos": 59, "dias_requeridos": 365,
                          "dias_faltantes": 306}},
            {"tool": "emitir_decision", "input": {
                "informe_id": "INF-002", "decision": "Negado",
            }, "output": {"ok": True, "decision_id": "DEC-INF-002-CAR"}},
        ]
        decision = {
            "decision": "Negado",
            "justificacion": (
                "Se niega la pre-autorización. La póliza tiene 59 días desde su alta, pero el "
                "procedimiento Cirugía bariátrica - bypass gástrico requiere un período de "
                "carencia de 365 días. Aprobación posible a partir del 2027-04-21."
            ),
            "clausula_aplicada": "Cláusula 3.1 — Período de carencia",
            "documentos_faltantes": [],
        }
    else:  # INF-003
        trace += [
            {"tool": "get_cobertura", "input": {"plan_id": "plan_estandar", "codigo_cpt": "47562"},
             "output": {"cubierto": True, "dias_carencia": 90,
                        "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos",
                                                  "segundo_dictamen"]}},
            {"tool": "verificar_carencia", "input": {
                "fecha_alta_poliza": inf["poliza_fecha_alta"],
                "fecha_evento": inf["fecha_programada"],
                "dias_carencia_requeridos": 90,
            }, "output": {"cumple": True, "dias_transcurridos": 372, "dias_requeridos": 90,
                          "dias_faltantes": 0}},
            {"tool": "validar_documentos", "input": {
                "documentos_requeridos": ["informe_quirurgico", "examenes_prequirurgicos",
                                          "segundo_dictamen"],
                "documentos_adjuntos": inf["documentos_adjuntos"],
            }, "output": {"completo": False,
                          "documentos_faltantes": ["examenes_prequirurgicos", "segundo_dictamen"]}},
            {"tool": "emitir_decision", "input": {
                "informe_id": "INF-003", "decision": "Documentos_Faltantes",
            }, "output": {"ok": True, "decision_id": "DEC-INF-003-DOC"}},
        ]
        decision = {
            "decision": "Documentos_Faltantes",
            "justificacion": (
                "Para procesar la pre-autorización de la Colecistectomía laparoscópica, se "
                "requieren los siguientes documentos adicionales: Exámenes prequirúrgicos, "
                "Segundo dictamen médico. Una vez completados, reenvíe el caso."
            ),
            "clausula_aplicada": "Cláusula 5.4 — Documentación mínima requerida",
            "documentos_faltantes": ["examenes_prequirurgicos", "segundo_dictamen"],
        }

    return {
        "trace": trace,
        "final_text": decision["justificacion"],
        "decision": decision,
    }


class StubHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: object) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path == "/health":
            return self._send(200, {"ok": True})
        if self.path == "/informes":
            return self._send(200, [
                {"id_informe": k,
                 "descripcion_procedimiento": v["descripcion_procedimiento"],
                 "hospital": v["hospital"]}
                for k, v in INFORMES.items()
            ])
        if self.path.startswith("/informes/"):
            informe_id = self.path[len("/informes/"):]
            inf = INFORMES.get(informe_id)
            if inf is None:
                return self._send(404, {"detail": f"informe {informe_id} no encontrado"})
            return self._send(200, inf)
        if self.path.startswith("/coberturas/"):
            # /coberturas/<cpt>/<plan_id>
            parts = self.path[len("/coberturas/"):].split("/")
            if len(parts) == 2:
                cpt, plan_id = parts
                cob = COBERTURAS.get((cpt, plan_id))
                if cob is None:
                    return self._send(404, {"cubierto": False, "motivo": f"sin regla para CPT {cpt} bajo {plan_id}"})
                return self._send(200, cob)
        self._send(404, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/procesar/"):
            informe_id = self.path[len("/procesar/"):]
            if informe_id not in INFORMES:
                return self._send(404, {"detail": f"informe {informe_id} no encontrado"})
            # Simulate the agent's thinking time. Configurable via env var so
            # devs can exercise the procesando timeline under realistic loads
            # (~5-15s) or the cold-wake path (>30s).
            sleep_s = float(os.environ.get("STUB_PROCESAR_SLEEP_S", "1.0"))
            time.sleep(sleep_s)
            return self._send(200, _trace_for(informe_id))
        self._send(404, {"detail": "not found"})

    def log_message(self, fmt: str, *args) -> None:  # quiet stdlib logging
        pass


if __name__ == "__main__":
    # Bind to localhost-only by default (safer for Codespaces / public dev
    # environments). Set STUB_BIND_ALL=1 to opt into 0.0.0.0.
    bind = "0.0.0.0" if os.environ.get("STUB_BIND_ALL") else "127.0.0.1"
    port = int(os.environ.get("STUB_PORT", "8000"))
    # ThreadingHTTPServer matches FastAPI's concurrent behavior so parallel
    # requests from the bandeja screen don't serialize, hiding the parallelism
    # benefit during local dev.
    print(f"dev stub backend listening on http://{bind}:{port}")
    ThreadingHTTPServer((bind, port), StubHandler).serve_forever()
