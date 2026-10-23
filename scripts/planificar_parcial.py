#!/usr/bin/env python3
"""Arma el sprint «Parcial» del tablero de Back End con las historias de la iteración 2.

    python3 scripts/planificar_parcial.py              # simula: no escribe nada
    python3 scripts/planificar_parcial.py --aplicar    # escribe en el tablero

    # opcional: borra el «Sprint 1» viejo, que queda vacío
    python3 scripts/planificar_parcial.py --aplicar --borrar-sprints-vacios

Hace cuatro cosas, en este orden:

  1. Saca del sprint «Parcial» todo lo que no es una historia de la iteración 2.
     Los tickets de la guía (pasos 1 a 47) no se tocan más que eso: ya están
     terminados.
  2. Crea el sprint «Parcial» (o reusa el que ya exista con ese nombre).
  3. Crea seis épicas y un ticket por historia, todos dentro del sprint, en
     «Por hacer» y con fechas planificadas. Deja el texto de cada épica y de cada
     ticket igual al de docs/historias-de-usuario.md: la historia completa en la
     descripción y la lista completa en los criterios de aceptación. Si el
     documento cambia, volver a correr el script baja el texto nuevo (los
     criterios que no cambiaron conservan su tilde).
  4. Anota las dependencias, que son las flechas del Gantt de la materia.

La cursada trabaja sin equipos: todo vive en el tablero de la materia.

El texto sale del documento y no se copia acá: el documento es la única fuente.
Lo que vive en este archivo es solo la planificación (fechas, puntos,
prioridad y dependencias).

Se puede volver a correr: lo que ya existe (sprint, épicas o tickets con el
mismo título) se reusa y no se duplica.

Para --aplicar hacen falta las credenciales de una cuenta docente de la materia.
Se leen de TABLERO_EMAIL y TABLERO_PASSWORD; si no están, se piden por consola.
Solo usa la biblioteca estándar de Python.
"""
import argparse
import datetime as dt
import getpass
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

API = "https://api-backend.bonini.com.ar/api"
GUIA = "backend"
DOCUMENTO = pathlib.Path(__file__).resolve().parent.parent / "docs" / "historias-de-usuario.md"

SPRINT = {
    "name": "Parcial",
    "description": "Iteración 2 del Banco de Proyectos: carga por la institución, materia, equipos, alumno y buscador.",
    "startsOn": "2026-10-26",
    "endsOn": "2026-11-20",
    "order": 2,
    "color": "#0ea5e9",
}

# El id es la letra de la épica en el documento («## Épica A — ...»).
EPICAS = [
    {"id": "C", "title": "Iteración 2 · Materia y cursada", "color": "#7c3aed"},
    {"id": "A", "title": "Iteración 2 · Carga por la institución", "color": "#2563eb"},
    {"id": "D", "title": "Iteración 2 · Equipos", "color": "#0891b2"},
    {"id": "B", "title": "Iteración 2 · Ficha del proyecto", "color": "#16a34a"},
    {"id": "E", "title": "Iteración 2 · Alumno", "color": "#d97706"},
    {"id": "F", "title": "Iteración 2 · Buscador", "color": "#dc2626"},
]

# `depende`: no se puede empezar antes de que termine la otra. Son las flechas
# del Gantt. El plan está armado en dos líneas de trabajo que avanzan en
# paralelo (primero el modelo académico, después la ficha y el buscador).
HISTORIAS = [
    # Línea 1: modelo académico
    {"id": "HU-07", "epica": "C", "puntos": 5, "prioridad": "high", "inicio": "2026-10-26", "fin": "2026-10-30"},
    {"id": "HU-01", "epica": "A", "puntos": 3, "prioridad": "high", "inicio": "2026-10-26", "fin": "2026-10-28"},
    {"id": "HU-02", "epica": "A", "puntos": 3, "prioridad": "high", "inicio": "2026-10-29", "fin": "2026-11-02"},
    {"id": "HU-03", "epica": "A", "puntos": 3, "prioridad": "high", "inicio": "2026-11-03", "fin": "2026-11-05",
     "depende": ["HU-02"]},
    {"id": "HU-04", "epica": "A", "puntos": 3, "prioridad": "medium", "inicio": "2026-11-02", "fin": "2026-11-04",
     "depende": ["HU-07"]},
    {"id": "HU-09", "epica": "D", "puntos": 5, "prioridad": "high", "inicio": "2026-11-05", "fin": "2026-11-11",
     "depende": ["HU-01"]},
    {"id": "HU-10", "epica": "D", "puntos": 5, "prioridad": "high", "inicio": "2026-11-12", "fin": "2026-11-18",
     "depende": ["HU-09"]},
    # Línea 2: ficha del proyecto, alumno y buscador
    {"id": "HU-08", "epica": "B", "puntos": 2, "prioridad": "high", "inicio": "2026-10-26", "fin": "2026-10-27"},
    {"id": "HU-05", "epica": "B", "puntos": 1, "prioridad": "medium", "inicio": "2026-10-28", "fin": "2026-10-28"},
    {"id": "HU-06", "epica": "B", "puntos": 3, "prioridad": "high", "inicio": "2026-10-29", "fin": "2026-11-02"},
    {"id": "HU-11", "epica": "E", "puntos": 5, "prioridad": "high", "inicio": "2026-10-26", "fin": "2026-11-02",
     "nota": "Toca `academics` al mismo tiempo que HU-07. Antes de `makemigrations`, hacer pull "
             "de `main`; si dos migraciones quedan con el mismo número, resolverlo con "
             "`makemigrations --merge` en el mismo PR."},
    {"id": "HU-12", "epica": "E", "puntos": 2, "prioridad": "medium", "inicio": "2026-11-03", "fin": "2026-11-04",
     "depende": ["HU-11"]},
    {"id": "HU-13", "epica": "F", "puntos": 5, "prioridad": "high", "inicio": "2026-11-03", "fin": "2026-11-09",
     "depende": ["HU-08", "HU-07"]},
    {"id": "HU-14", "epica": "F", "puntos": 3, "prioridad": "medium", "inicio": "2026-11-05", "fin": "2026-11-09",
     "depende": ["HU-07"]},
    {"id": "HU-16", "epica": "F", "puntos": 3, "prioridad": "medium", "inicio": "2026-11-10", "fin": "2026-11-12",
     "depende": ["HU-07"]},
    {"id": "HU-17", "epica": "F", "puntos": 2, "prioridad": "medium", "inicio": "2026-11-10", "fin": "2026-11-11",
     "depende": ["HU-13"]},
    {"id": "HU-15", "epica": "F", "puntos": 3, "prioridad": "medium", "inicio": "2026-11-12", "fin": "2026-11-16",
     "depende": ["HU-17"]},
]

PRIORIDAD = {"high": "Alta", "medium": "Media"}
LARGO_DE_UN_CRITERIO = 300  # el máximo que acepta el tablero (Criterion.text)


# --------------------------------------------------------------------------
# El texto: sale del documento
# --------------------------------------------------------------------------

def leer_documento(ruta=DOCUMENTO):
    """Las historias y las épicas del documento, ya listas para el tablero.

    Devuelve dos diccionarios:
      historias  {"HU-07": {"titulo", "descripcion", "criterios"}}
      epicas     {"A": "texto de la introducción de la épica"}
    """
    texto = ruta.read_text(encoding="utf-8")
    historias, epicas = {}, {}
    epica_actual, historia_actual, lineas = None, None, []

    def cerrar():
        if historia_actual is not None:
            historias[historia_actual["id"]] = _armar_historia(historia_actual, lineas)
        elif epica_actual is not None:
            intro = _limpiar(lineas)
            if intro:
                epicas[epica_actual] = intro

    for linea in texto.splitlines():
        epica = re.match(r"^## Épica ([A-Z]) — ", linea)
        historia = re.match(r"^### (HU-\d+) — (.+)$", linea)
        corte = linea.startswith("## ") or linea.strip() == "---"
        if epica or historia or corte:
            cerrar()
            lineas = []
            if epica:
                epica_actual, historia_actual = epica.group(1), None
            elif historia:
                historia_actual = {"id": historia.group(1), "titulo": historia.group(2).strip()}
            else:
                epica_actual, historia_actual = None, None
            continue
        lineas.append(linea)
    cerrar()
    return historias, epicas


def _armar_historia(cabecera, lineas):
    """Separa la lista de criterios del resto: los criterios van a su campo y
    todo lo demás (historia, «Hoy», notas, tests, lo que hay que confirmar) a la
    descripción."""
    descripcion, items = [], []  # items: [texto, [sub-ítems]]
    en_criterios = False
    for linea in lineas:
        if linea.strip() == "**Criterios de aceptación**":
            en_criterios = True
            continue
        if en_criterios:
            item = re.match(r"^(\s*)- (.+)$", linea)
            if item and not item.group(1):
                items.append([item.group(2).strip(), []])
                continue
            if item and items:
                items[-1][1].append(item.group(2).strip())
                continue
            if not linea.strip():
                continue
            en_criterios = False
        descripcion.append(linea)
    return {
        "titulo": cabecera["titulo"],
        "descripcion": _limpiar(descripcion),
        "criterios": [c for texto, subs in items for c in _criterios_de(texto, subs)],
    }


def _criterios_de(texto, subs):
    """Un ítem con sub-ítems («Endpoints: - GET ... - POST ...») va en un solo
    criterio si entra; si no, cada sub-ítem es un criterio propio que lleva
    adelante el texto de arriba, así se entiende suelto y se tilda por separado."""
    if not subs:
        return [texto]
    junto = texto + (" " if texto.endswith(":") else ": ") + "; ".join(subs)
    if len(junto) <= LARGO_DE_UN_CRITERIO:
        return [junto]
    contexto = texto.rstrip(":").rstrip()
    return [f"{contexto} — {sub}" for sub in subs]


def _limpiar(lineas):
    """El Markdown del documento, llevado a lo que la ficha del ticket sabe
    mostrar: negrita, código, listas y enlaces. Las citas («> ») pasan a ser
    párrafos comunes."""
    salida = []
    for linea in lineas:
        linea = re.sub(r"^>\s?", "", linea)
        salida.append(linea.rstrip())
    return "\n".join(salida).strip()


def titulo_ticket(historia_id, textos):
    return f"{historia_id} · {textos[historia_id]['titulo']}"


def descripcion(h, textos, intros):
    """La historia entera del documento, el contexto de su épica y lo que dice el
    plan del sprint: todo lo que hace falta para hacer el ticket sin abrir nada más."""
    partes = [textos[h["id"]]["descripcion"]]
    if intros.get(h["epica"]):
        partes.append("**Contexto de la épica**\n" + intros[h["epica"]])
    plan = []
    if h.get("depende"):
        plan.append(f"- Depende de {', '.join(h['depende'])}: no se puede empezar antes de que termine.")
    if h.get("nota"):
        plan.append(f"- {h['nota']}")
    if plan:
        partes.append("**Planificación del sprint**\n" + "\n".join(plan))
    return "\n\n".join(partes)


# --------------------------------------------------------------------------
# Comprobaciones del plan: corren siempre, también al simular
# --------------------------------------------------------------------------

def _fecha(texto):
    return dt.date.fromisoformat(texto)


def validar_plan(textos):
    errores = []
    inicio_sprint, fin_sprint = _fecha(SPRINT["startsOn"]), _fecha(SPRINT["endsOn"])
    por_id = {h["id"]: h for h in HISTORIAS}

    sobrantes = set(textos) - set(por_id)
    if sobrantes:
        errores.append(f"el documento tiene historias sin planificar: {', '.join(sorted(sobrantes))}")

    for h in HISTORIAS:
        if h["id"] not in textos:
            errores.append(f"{h['id']}: no está en el documento")
            continue
        if not textos[h["id"]]["criterios"]:
            errores.append(f"{h['id']}: el documento no trae criterios de aceptación")
        for criterio in textos[h["id"]]["criterios"]:
            if len(criterio) > LARGO_DE_UN_CRITERIO:
                errores.append(f"{h['id']}: un criterio pasa los {LARGO_DE_UN_CRITERIO} caracteres: «{criterio[:60]}…»")
        ini, fin = _fecha(h["inicio"]), _fecha(h["fin"])
        if not (inicio_sprint <= ini <= fin <= fin_sprint):
            errores.append(f"{h['id']}: sus fechas quedan fuera del sprint")
        if ini.weekday() > 4 or fin.weekday() > 4:
            errores.append(f"{h['id']}: empieza o termina un fin de semana")
        for dep in h.get("depende", []):
            if _fecha(por_id[dep]["fin"]) >= ini:
                errores.append(f"{h['id']}: empieza antes de que termine {dep}")
    return errores


def rango_epica(epica_id):
    propias = [h for h in HISTORIAS if h["epica"] == epica_id]
    return min(h["inicio"] for h in propias), max(h["fin"] for h in propias)


def imprimir_plan(textos):
    puntos = sum(h["puntos"] for h in HISTORIAS)
    print(f"Sprint: {SPRINT['name']} · {SPRINT['startsOn']} → {SPRINT['endsOn']} · {puntos} puntos")
    for epica in EPICAS:
        desde, hasta = rango_epica(epica["id"])
        print(f"\n  [{epica['title']}] {desde} → {hasta}")
        for h in sorted((h for h in HISTORIAS if h["epica"] == epica["id"]), key=lambda h: h["inicio"]):
            deps = h.get("depende", [])
            print(
                f"    {h['id']} {h['inicio'][5:]}→{h['fin'][5:]} {h['puntos']}p "
                f"{PRIORIDAD[h['prioridad']]:<5} {textos[h['id']]['titulo']} "
                f"({len(textos[h['id']]['criterios'])} criterios)"
                + (f"  (después de {', '.join(deps)})" if deps else "")
            )


# --------------------------------------------------------------------------
# La API
# --------------------------------------------------------------------------

class Api:
    def __init__(self, base, token=None):
        self.base = base.rstrip("/")
        self.token = token

    def pedir(self, metodo, ruta, datos=None):
        cuerpo = json.dumps(datos).encode() if datos is not None else None
        pedido = urllib.request.Request(self.base + ruta, data=cuerpo, method=metodo)
        pedido.add_header("Content-Type", "application/json")
        # Cloudflare rechaza el User-Agent por defecto de urllib (error 1010).
        pedido.add_header("User-Agent", "campuslab-planificar-parcial/1.0")
        if self.token:
            pedido.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(pedido, timeout=30) as respuesta:
                texto = respuesta.read().decode()
        except urllib.error.HTTPError as exc:
            sys.exit(f"{metodo} {ruta} respondió {exc.code}: {exc.read().decode()[:500]}")
        return json.loads(texto) if texto else None

    def get(self, ruta):
        return self.pedir("GET", ruta)

    def post(self, ruta, datos):
        return self.pedir("POST", ruta, datos)

    def patch(self, ruta, datos):
        return self.pedir("PATCH", ruta, datos)

    def delete(self, ruta):
        return self.pedir("DELETE", ruta)


def todos_los_tickets(api):
    """Los tickets de la materia: los del backlog y los que están en algún tablero."""
    tickets = {}
    backlog = api.get(f"/equipos/backlog?guia={GUIA}")
    for epica in backlog["epics"]:
        for t in epica["tasks"]:
            tickets[t["id"]] = t
    for t in backlog["loose"]:
        tickets[t["id"]] = t
    for columna in api.get(f"/equipos/board?guia={GUIA}")["columns"]:
        for t in columna["tasks"]:
            tickets[t["id"]] = t
    return list(tickets.values())


def todas_las_epicas(api):
    return api.get(f"/equipos/backlog?guia={GUIA}")["epics"]


def fuera_del_parcial(api, aplicar, textos):
    """Paso 1: en el Parcial van sólo las historias de la iteración 2. Lo demás
    (los tickets de la guía) sale del sprint y queda en la columna en la que
    esté: no se lo devuelve al backlog ni se lo mueve."""
    propios = {titulo_ticket(h["id"], textos) for h in HISTORIAS}
    cambios = 0
    for t in sorted(todos_los_tickets(api), key=lambda t: t["number"]):
        if t["title"] in propios or t["sprintName"] != SPRINT["name"]:
            continue
        print(f"  {t['key']} sale de «{t['sprintName']}»")
        if aplicar:
            api.patch(f"/equipos/tasks/{t['id']}", {"sprintId": 0})
        cambios += 1
    if not cambios:
        print("  nada que sacar: en el Parcial están sólo las historias nuevas")


def asegurar_sprint(api, aplicar):
    """Paso 2."""
    for sprint in api.get(f"/equipos/sprints?guia={GUIA}"):
        if sprint["name"] == SPRINT["name"]:
            print(f"  ya existe «{SPRINT['name']}» (id {sprint['id']})")
            return sprint["id"]
    print(f"  crea «{SPRINT['name']}»")
    if not aplicar:
        return None
    sprints = api.post("/equipos/sprints", {**SPRINT, "guide": GUIA})
    return next(s["id"] for s in sprints if s["name"] == SPRINT["name"])


def borrar_sprints_vacios(api, aplicar):
    """Opcional: los sprints viejos que quedaron sin tickets después del paso 1.

    El Gantt se dibuja desde el primer sprint de la materia, así que un sprint
    vacío de septiembre deja semanas en blanco adelante del Parcial.
    """
    en_uso = {t["sprintId"] for t in todos_los_tickets(api)}
    for sprint in api.get(f"/equipos/sprints?guia={GUIA}"):
        if sprint["name"] == SPRINT["name"]:
            continue
        if aplicar and sprint["id"] in en_uso:
            print(f"  deja «{sprint['name']}»: todavía tiene tickets")
            continue
        print(f"  borra «{sprint['name']}» ({sprint['startsOn']} → {sprint['endsOn']})")
        if aplicar:
            api.delete(f"/equipos/sprints/{sprint['id']}")


def asegurar_epicas(api, aplicar, intros):
    """Paso 3a: las épicas nacen en el backlog y se reparten al final."""
    existentes = {e["title"]: e for e in todas_las_epicas(api)}
    ids = {}
    for orden, epica in enumerate(EPICAS, start=101):
        texto = intros.get(epica["id"], "")
        if epica["title"] in existentes:
            ya = existentes[epica["title"]]
            ids[epica["id"]] = ya["id"]
            if (ya.get("description") or "") != texto:
                print(f"  actualiza el texto de [{epica['title']}]")
                if aplicar:
                    api.patch(f"/equipos/epics/{ya['id']}", {"description": texto})
            else:
                print(f"  ya existe [{epica['title']}]")
            continue
        print(f"  crea [{epica['title']}]")
        if not aplicar:
            continue
        desde, hasta = rango_epica(epica["id"])
        backlog = api.post(
            "/equipos/epics",
            {
                "title": epica["title"], "description": texto, "color": epica["color"],
                "order": orden, "guide": GUIA, "startsOn": desde, "endsOn": hasta,
            },
        )
        ids[epica["id"]] = next(e["id"] for e in backlog["epics"] if e["title"] == epica["title"])
    return ids


def asegurar_tickets(api, aplicar, sprint_id, epicas, textos, intros):
    """Paso 3b y 4: un ticket por historia, adentro del sprint, con sus fechas y
    con el texto completo del documento."""
    existentes = {t["title"]: t["id"] for t in todos_los_tickets(api)}
    ids = {}
    for h in HISTORIAS:
        titulo = titulo_ticket(h["id"], textos)
        texto = descripcion(h, textos, intros)
        criterios = textos[h["id"]]["criterios"]

        if titulo in existentes:
            ids[h["id"]] = existentes[titulo]
            detalle = api.get(f"/equipos/tasks/{existentes[titulo]}")
            actuales = [c["text"] for c in detalle["criteria"]]
            if detalle["task"]["description"] == texto and actuales == criterios:
                print(f"  ya existe {titulo}")
                continue
            print(f"  actualiza el texto de {titulo} ({len(criterios)} criterios)")
            if aplicar:
                api.patch(
                    f"/equipos/tasks/{existentes[titulo]}",
                    {"description": texto, "criteria": criterios},
                )
            continue

        print(f"  crea {titulo} ({len(criterios)} criterios)")
        if not aplicar:
            continue
        backlog = api.post(
            "/equipos/tasks",
            {
                "title": titulo, "description": texto, "type": "story",
                "priority": h["prioridad"], "storyPoints": h["puntos"],
                "epicId": epicas[h["epica"]], "sprintId": sprint_id, "guide": GUIA,
                "plannedStart": h["inicio"], "plannedEnd": h["fin"], "criteria": criterios,
                "status": "todo",
            },
        )
        ids[h["id"]] = next(t["id"] for t in todos_los_tickets(api) if t["title"] == titulo)
    return ids


def tablero_y_dependencias(api, aplicar, tickets):
    """Paso 4: las historias van al tablero («Por hacer») si quedaron en el
    backlog, y se anotan sus dependencias, que son las flechas del Gantt."""
    por_id = {t["id"]: t for t in todos_los_tickets(api)} if aplicar else {}
    for h in HISTORIAS:
        ticket = por_id.get(tickets.get(h["id"]))
        if ticket and ticket["status"] == "backlog":
            print(f"  {h['id']} pasa a «Por hacer»")
            api.post(f"/equipos/tasks/{ticket['id']}/move", {"status": "todo"})

    for h in HISTORIAS:
        for dep in h.get("depende", []):
            if not aplicar:
                print(f"  {h['id']} depende de {dep}")
                continue
            detalle = api.get(f"/equipos/tasks/{tickets[h['id']]}")["task"]
            if any(d["id"] == tickets[dep] for d in detalle["dependsOn"]):
                continue
            print(f"  {h['id']} depende de {dep}")
            api.post(f"/equipos/tasks/{tickets[h['id']]}/dependencies", {"dependsOnId": tickets[dep]})


def login(api):
    email = os.environ.get("TABLERO_EMAIL") or input("Email del docente: ").strip()
    clave = os.environ.get("TABLERO_PASSWORD") or getpass.getpass("Clave: ")
    sesion = api.post("/auth/login", {"email": email, "password": clave})
    return sesion["access"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--aplicar", action="store_true", help="Escribe en el tablero. Sin esto, solo simula.")
    parser.add_argument("--api", default=API, help=f"Dirección de la API (por defecto {API}).")
    parser.add_argument(
        "--borrar-sprints-vacios",
        action="store_true",
        help="Borra los sprints viejos que quedan sin tickets (si no, el Gantt arranca en el primero).",
    )
    parser.add_argument(
        "--mostrar",
        metavar="HU",
        help="Muestra cómo queda el texto de un ticket (por ejemplo HU-09) y termina.",
    )
    opciones = parser.parse_args()

    textos, intros = leer_documento()

    if opciones.mostrar:
        h = next((h for h in HISTORIAS if h["id"] == opciones.mostrar), None)
        if h is None:
            sys.exit(f"No hay ninguna historia {opciones.mostrar} en el plan.")
        print(titulo_ticket(h["id"], textos), "\n")
        print(descripcion(h, textos, intros), "\n")
        print("Criterios:")
        for criterio in textos[h["id"]]["criterios"]:
            print(f"  [ ] {criterio}")
        return

    errores = validar_plan(textos)
    if errores:
        sys.exit("El plan tiene errores:\n  " + "\n  ".join(errores))

    imprimir_plan(textos)

    api = Api(opciones.api)
    if opciones.aplicar:
        api.token = login(api)

    print("\n1. En el Parcial, sólo lo nuevo")
    fuera_del_parcial(api, opciones.aplicar, textos)
    print("\n2. Sprint")
    sprint_id = asegurar_sprint(api, opciones.aplicar)
    if opciones.borrar_sprints_vacios:
        borrar_sprints_vacios(api, opciones.aplicar)
    print("\n3. Épicas y tickets")
    epicas = asegurar_epicas(api, opciones.aplicar, intros)
    tickets = asegurar_tickets(api, opciones.aplicar, sprint_id, epicas, textos, intros)
    print("\n4. Tablero y dependencias")
    tablero_y_dependencias(api, opciones.aplicar, tickets)

    if not opciones.aplicar:
        print("\nSimulación: no se escribió nada. Para aplicarlo: --aplicar")
    else:
        print("\nListo. El Gantt de la materia está en #/gantt")


if __name__ == "__main__":
    main()
