import altair as alt
import pandas as pd
import streamlit as st

# =====================================================================
# PARÁMETROS: aquí cambias todo sin tocar el resto del código
# =====================================================================
ARCHIVO = "votacion_anonimo.csv"   # lo crea preparar_datos.py (sin datos personales)

TITULO_PAGINA = "Tablero de votación"
ICONO = "🗳️"
TITULO = "Tablero de posibles votantes"
DESCRIPCION = (
    "Solo conteos y totales: no contiene cédulas, nombres ni teléfonos. "
    "Usa los filtros de la barra lateral (en el celular, el botón » de arriba a la izquierda)."
)

# Columnas del CSV
COL_LIDER, COL_BARRIO, COL_PUESTO, COL_MESA = "Lider", "Barrio", "Puesto", "Mesa"
COL_ACTO, COL_OBS = "Acto", "Observacion"

# Texto del acto
ACTO_SI, ACTO_NO, ACTO_SIN = "SI", "NO", "SIN DATO"

# Cómo se puede agrupar el ranking: (nombre en el menú, columna)
AGRUPAR_POR = {"Líder": COL_LIDER, "Barrio": COL_BARRIO, "Puesto de votación": COL_PUESTO}
TOP_N_DEFAULT = 15

# Tarjetas de indicadores: (nombre en la tarjeta, qué calcular)
# Opciones: "registros", "acto_si", "pct_si", "acto_no", "con_obs",
#           "sin_cedula", "repetidas", "no_censo", "lideres", "barrios", "puestos"
TARJETAS = [
    ("Posibles votantes", "registros"),
    ("Acto: SÍ", "acto_si"),
    ("Acto: NO", "acto_no"),
    ("Con observación", "con_obs"),
]
TARJETAS_CALIDAD = [
    ("Cédulas repetidas", "repetidas"),
    ("Sin número de cédula", "sin_cedula"),
    ("No está en el censo", "no_censo"),
    ("Líderes", "lideres"),
]

# =====================================================================
# CÓDIGO (no necesitas cambiar nada de aquí hacia abajo)
# =====================================================================
st.set_page_config(
    page_title=TITULO_PAGINA, page_icon=ICONO, layout="wide",
    initial_sidebar_state="auto",
)

# Ajustes para celular: menos márgenes, texto compacto y tarjetas de 2 en 2.
st.markdown(
    """
    <style>
    @media (max-width: 640px) {
        .block-container { padding: 1rem 0.75rem 3rem 0.75rem; }
        h1 { font-size: 1.6rem !important; }
        h2 { font-size: 1.3rem !important; }
        h3 { font-size: 1.1rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.5rem; }
        [data-testid="stMetricLabel"] p { font-size: 0.8rem; }
        .st-key-tarjetas [data-testid="stColumn"],
        .st-key-calidad [data-testid="stColumn"] {
            min-width: calc(50% - 0.5rem) !important;
            flex: 1 1 calc(50% - 0.5rem) !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def cargar():
    d = pd.read_csv(ARCHIVO, encoding="utf-8-sig")
    d[COL_OBS] = d[COL_OBS].fillna("")
    return d


df = cargar()

st.title(f"{ICONO} {TITULO}")
st.caption(DESCRIPCION)

# ---------------- Barra lateral: filtros ----------------
st.sidebar.header("Filtros")
st.sidebar.caption("Si no eliges nada en un filtro, se muestran todos.")

sel_lider = st.sidebar.multiselect("Líder", sorted(df[COL_LIDER].unique()))
sel_barrio = st.sidebar.multiselect("Barrio", sorted(df[COL_BARRIO].unique()))
sel_puesto = st.sidebar.multiselect("Puesto de votación", sorted(df[COL_PUESTO].unique()))
sel_acto = st.sidebar.multiselect("Acto", [ACTO_SI, ACTO_NO, ACTO_SIN])
sin_repetidos = st.sidebar.checkbox("Quitar cédulas repetidas", value=True)

filtrado = df.copy()
for col, sel in [(COL_LIDER, sel_lider), (COL_BARRIO, sel_barrio),
                 (COL_PUESTO, sel_puesto), (COL_ACTO, sel_acto)]:
    if sel:
        filtrado = filtrado[filtrado[col].isin(sel)]
con_repetidas = filtrado  # se guarda para poder contar las cédulas repetidas
if sin_repetidos:
    filtrado = filtrado[~filtrado["Cedula_repetida"]]

st.sidebar.divider()
st.sidebar.caption(f"Registros con los filtros actuales: {len(filtrado)} de {len(df)}")

if filtrado.empty:
    st.warning("No hay registros con los filtros elegidos. Cambia los filtros de la barra lateral.")
    st.stop()

# ---------------- Indicadores ----------------
n = len(filtrado)
si = int((filtrado[COL_ACTO] == ACTO_SI).sum())
CALCULOS = {
    "registros": lambda: f"{n:,}",
    "acto_si": lambda: f"{si:,}",
    "pct_si": lambda: f"{si / n * 100:.1f}%",
    "acto_no": lambda: f"{int((filtrado[COL_ACTO] == ACTO_NO).sum()):,}",
    "con_obs": lambda: f"{int((filtrado[COL_OBS] != '').sum()):,}",
    "sin_cedula": lambda: f"{int(filtrado['Sin_cedula'].sum()):,}",
    "repetidas": lambda: f"{int(con_repetidas['Cedula_repetida'].sum()):,}",
    "no_censo": lambda: f"{int(filtrado['No_en_censo'].sum()):,}",
    "lideres": lambda: f"{filtrado[COL_LIDER].nunique():,}",
    "barrios": lambda: f"{filtrado[COL_BARRIO].nunique():,}",
    "puestos": lambda: f"{filtrado[COL_PUESTO].nunique():,}",
}


COLORES = {"Acto SÍ": "#2e9d57", "Acto NO": "#d64545", "Sin dato de acto": "#9aa3ad"}


def barras_horizontales(tabla, columnas, colores=None):
    """Barras horizontales apiladas, ordenadas de mayor a menor total."""
    largo = tabla[columnas].reset_index()
    nombre_indice = largo.columns[0]
    largo = largo.melt(id_vars=nombre_indice, var_name="Serie", value_name="Cantidad")
    orden = tabla[columnas].sum(axis=1).sort_values(ascending=False).index.tolist()
    color = (
        alt.Color("Serie:N", title=None,
                  scale=alt.Scale(domain=list(colores), range=list(colores.values())),
                  legend=alt.Legend(orient="bottom"))
        if colores else alt.value("#3b82c4")
    )
    grafico = (
        alt.Chart(largo)
        .mark_bar()
        .encode(
            y=alt.Y(f"{nombre_indice}:N", sort=orden, title=None,
                    axis=alt.Axis(labelLimit=220, labelOverlap=False, labelFontSize=11)),
            x=alt.X("Cantidad:Q", title=None),
            color=color,
            tooltip=[nombre_indice, "Serie", "Cantidad"],
        )
        .properties(height=max(120, 28 * len(orden)))
    )
    st.altair_chart(grafico, width="stretch")


def tarjetas(lista, clave):
    with st.container(key=clave):
        for col, (nombre, calculo) in zip(st.columns(len(lista)), lista):
            with col:
                with st.container(border=True):
                    st.metric(nombre, CALCULOS[calculo]())


st.header("Resumen general")
tarjetas(TARJETAS, "tarjetas")

# ---------------- Ranking interactivo ----------------
st.header("Ranking")
c1, c2 = st.columns([2, 1])
with c1:
    dim_nombre = st.selectbox("Agrupar por", list(AGRUPAR_POR))
with c2:
    top_n = st.slider("Mostrar los primeros", 5, 50, TOP_N_DEFAULT)
dim = AGRUPAR_POR[dim_nombre]

rank = (
    filtrado.assign(
        **{"Acto SÍ": filtrado[COL_ACTO] == ACTO_SI,
           "Acto NO": filtrado[COL_ACTO] == ACTO_NO,
           "Sin dato de acto": filtrado[COL_ACTO] == ACTO_SIN,
           "Con observación": filtrado[COL_OBS] != ""}
    )
    .groupby(dim)[["Acto SÍ", "Acto NO", "Sin dato de acto", "Con observación"]]
    .sum()
)
rank.insert(0, "Total", rank[["Acto SÍ", "Acto NO", "Sin dato de acto"]].sum(axis=1))
rank["% Acto SÍ"] = rank["Acto SÍ"] / rank["Total"] * 100
rank = rank.sort_values("Total", ascending=False)
top = rank.head(top_n)

with st.container(border=True):
    st.subheader(f"Votantes por {dim_nombre.lower()} (primeros {len(top)})")
    barras_horizontales(top, ["Acto SÍ", "Acto NO", "Sin dato de acto"], COLORES)

with st.container(border=True):
    st.subheader(f"Tabla por {dim_nombre.lower()}")
    st.dataframe(
        rank.style.format({"% Acto SÍ": "{:.1f}%"}),
        width="stretch",
    )
    st.download_button(
        "⬇️ Descargar esta tabla (CSV)",
        rank.to_csv().encode("utf-8-sig"),
        file_name=f"votantes_por_{dim_nombre.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )

# ---------------- Mesas de un puesto ----------------
st.header("Mesas por puesto de votación")
puestos_orden = filtrado[COL_PUESTO].value_counts().index.tolist()
puesto_ver = st.selectbox("Puesto", puestos_orden)
mesas = (
    filtrado[(filtrado[COL_PUESTO] == puesto_ver) & filtrado[COL_MESA].notna()]
    .groupby(COL_MESA).size().rename("Votantes")
)
with st.container(border=True):
    st.subheader(f"Votantes por mesa - {puesto_ver}")
    if mesas.empty:
        st.info("Este puesto no tiene número de mesa registrado.")
    else:
        mesas.index = mesas.index.astype(int).astype(str)
        st.bar_chart(mesas)

# ---------------- Observaciones y calidad de los datos ----------------
st.header("Observaciones y calidad de la base")
tarjetas(TARJETAS_CALIDAD, "calidad")
obs = filtrado[filtrado[COL_OBS] != ""].groupby(COL_OBS).size().sort_values(ascending=False)
with st.container(border=True):
    st.subheader("Observaciones registradas")
    if obs.empty:
        st.info("No hay observaciones con estos filtros.")
    else:
        barras_horizontales(obs.rename("Registros").to_frame(), ["Registros"])
