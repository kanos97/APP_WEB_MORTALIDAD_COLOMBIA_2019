#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table
import pathlib
import plotly.graph_objects as go

def blank_fig(title="Sin datos"):
    fig = go.Figure()
    fig.update_layout(
        title=title, xaxis_visible=False, yaxis_visible=False,
        annotations=[dict(text="Sin datos", x=0.5, y=0.5, showarrow=False, xref="paper", yref="paper")]
    )
    return fig

# ====== Paths ======
BASE_DIR = pathlib.Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
CENTROIDS_PATH = BASE_DIR / "departments_centroids.json"

# ====== Load data ======
# Mortalidad 2019 (no fetales)
df = pd.read_excel(DATA_DIR / "NoFetal2019.xlsx", sheet_name="No_Fetales_2019")

# Divipola (para nombres de departamento y municipio)
divi = pd.read_excel(DATA_DIR / "Divipola.xlsx", sheet_name=0)

# Catálogo CIE-10 mortalidad (para nombres de causa)
# Detectar encabezado correcto de forma robusta
codigos_raw = pd.read_excel(DATA_DIR / "CodigosDeMuerte.xlsx", sheet_name=0, header=None)
header_row_idx = None
for idx, row in codigos_raw.iterrows():
    joined = " ".join([str(x) for x in row.tolist()]).lower()
    if "código de la cie-10 cuatro caracteres" in joined or "codigo de la cie-10 cuatro caracteres" in joined:
        header_row_idx = idx
        break
if header_row_idx is None:
    header_row_idx = 0
codigos = pd.read_excel(DATA_DIR / "CodigosDeMuerte.xlsx", sheet_name=0, header=header_row_idx)

# Normalizar columnas (quitar espacios dobles, bajar a minúsculas)
def normalize_cols(df_):
    df_ = df_.copy()
    df_.columns = (
        df_.columns
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return df_

df = normalize_cols(df)
divi = normalize_cols(divi)
codigos = normalize_cols(codigos)

# Columnas clave esperadas
# df: 'AÑO','MES','COD_DEPARTAMENTO','COD_MUNICIPIO','SEXO','GRUPO_EDAD1','MANERA_MUERTE','COD_MUERTE'
# divi: 'COD_DEPARTAMENTO','DEPARTAMENTO','COD_MUNICIPIO','MUNICIPIO'
# codigos: 'Código de la CIE-10 cuatro caracteres','Descripcion de códigos mortalidad a cuatro caracteres'
# Ajuste por tildes y variaciones
def find_col(df_, candidates):
    cols = {c.lower(): c for c in df_.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    raise KeyError(f"No se encontró ninguna de las columnas esperadas: {candidates} en {list(df_.columns)}")

col_cod_dep = find_col(df, ["COD_DEPARTAMENTO"])
col_cod_mun = find_col(df, ["COD_MUNICIPIO"])
col_mes     = find_col(df, ["MES"])
col_ano     = find_col(df, ["AÑO", "ANO"])
col_sexo    = find_col(df, ["SEXO"])
col_grupo   = find_col(df, ["GRUPO_EDAD1","GRUPO_EDAD"])
col_manera  = find_col(df, ["MANERA_MUERTE"])
col_cod_cie = find_col(df, ["COD_MUERTE","COD_CAUSA","CAUSA_DEF_BASICA"])

divi_cod_dep = find_col(divi, ["COD_DEPARTAMENTO"])
divi_cod_mun = find_col(divi, ["COD_MUNICIPIO"])
divi_dep     = find_col(divi, ["DEPARTAMENTO"])
divi_mun     = find_col(divi, ["MUNICIPIO"])

cod_code4 = find_col(codigos, ["Código de la CIE-10 cuatro caracteres", "Codigo de la CIE-10 cuatro caracteres"])
cod_desc4 = find_col(codigos, ["Descripcion de códigos mortalidad a cuatro caracteres",
                               "Descripción de códigos mortalidad a cuatro caracteres",
                               "Descripcion de codigos mortalidad a cuatro caracteres"])

# Tipos
for c in [col_cod_dep, divi_cod_dep, col_cod_mun, divi_cod_mun, col_mes, col_ano]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if c in divi.columns:
        divi[c] = pd.to_numeric(divi[c], errors="coerce")

# Join con Divipola para nombre de departamento y municipio
df = df.merge(divi[[divi_cod_dep, divi_dep, divi_cod_mun, divi_mun]],
              left_on=[col_cod_dep, col_cod_mun],
              right_on=[divi_cod_dep, divi_cod_mun],
              how="left")

# Map sexo
sexo_map = {1: "Hombre", 2: "Mujer"}
df["SEXO_NOMBRE"] = df[col_sexo].map(sexo_map).fillna("No informado")

# Map grupos de edad (reemplazado por categorización agregada del usuario)

# === Categorización GRUPO_EDAD1 (tabla del usuario) ===
# Categorías y rangos aproximados:
# 0–4  -> Mortalidad neonatal (menor de 1 mes)
# 5–6  -> Mortalidad infantil (1 a 11 meses)
# 7–8  -> Primera infancia (1 a 4 años)
# 9–10 -> Niñez (5 a 14 años)
# 11   -> Adolescencia (15 a 19 años)
# 12–13-> Juventud (20 a 29 años)
# 14–16-> Adultez temprana (30 a 44 años)
# 17–19-> Adultez intermedia (45 a 59 años)
# 20–24-> Vejez (60 a 84 años)
# 25–28-> Longevidad / Centenarios (85 a 100+ años)
# 29   -> Edad desconocida

def grupo_edad_categoria(v):
    try:
        g = int(v)
    except Exception:
        return "Sin clasificar"
    if 0 <= g <= 4:
        return "Mortalidad neonatal (<1 mes)"
    if 5 <= g <= 6:
        return "Mortalidad infantil (1–11 meses)"
    if 7 <= g <= 8:
        return "Primera infancia (1–4 años)"
    if 9 <= g <= 10:
        return "Niñez (5–14 años)"
    if g == 11:
        return "Adolescencia (15–19)"
    if 12 <= g <= 13:
        return "Juventud (20–29)"
    if 14 <= g <= 16:
        return "Adultez temprana (30–44)"
    if 17 <= g <= 19:
        return "Adultez intermedia (45–59)"
    if 20 <= g <= 24:
        return "Vejez (60–84)"
    if 25 <= g <= 28:
        return "Longevidad / Centenarios (85–100+)"
    if g == 29:
        return "Edad desconocida"
    return "Sin clasificar"

df["EDAD_CATEGORIA"] = df[col_grupo].apply(grupo_edad_categoria)
ordered_age_categories = [
    "Mortalidad neonatal (<1 mes)",
    "Mortalidad infantil (1–11 meses)",
    "Primera infancia (1–4 años)",
    "Niñez (5–14 años)",
    "Adolescencia (15–19)",
    "Juventud (20–29)",
    "Adultez temprana (30–44)",
    "Adultez intermedia (45–59)",
    "Vejez (60–84)",
    "Longevidad / Centenarios (85–100+)",
    "Edad desconocida",
    "Sin clasificar"
]
# === Estandarizar código CIE-10 a 4 caracteres y construir catálogo ===
df["COD4"] = df[col_cod_cie].astype(str).str.strip().str[:4].str.upper()

# OJO: 'cod_code4' y 'cod_desc4' ya tuvieron que haberse detectado arriba con find_col(...)
codigos["COD4"] = codigos[cod_code4].astype(str).str.strip().str[:4].str.upper()

catalog = codigos[["COD4", cod_desc4]].drop_duplicates()
catalog.columns = ["COD4", "DESC_COD4"]

# Join con catálogo CIE-10 (dejamos tal cual)
df = df.merge(catalog, on="COD4", how="left")

# ====== Pre-aggregations ======
# Totales por departamento
dep_tot = df.groupby([col_cod_dep, divi_dep], dropna=False).size().reset_index(name="TOTAL")

# Cargar centroids
with open(CENTROIDS_PATH, "r", encoding="utf-8") as f:
    centroids = json.load(f)

dep_geo = []
for _, row in dep_tot.iterrows():
    code = int(row[col_cod_dep]) if pd.notna(row[col_cod_dep]) else None
    if code and str(code) in centroids:
        c = centroids[str(code)]
    else:
        c = centroids.get(code) or centroids.get(int(code)) if code is not None else None
    # fallback: try numeric key
    if c is None and code in centroids:
        c = centroids[code]
    if c is not None:
        dep_geo.append({
            "COD_DEPARTAMENTO": code,
            "DEPARTAMENTO": row[divi_dep],
            "TOTAL": int(row["TOTAL"]),
            "lat": c["lat"],
            "lon": c["lon"]
        })
dep_geo = pd.DataFrame(dep_geo)

# Serie mensual (2019)
serie_mes = df.groupby(col_mes).size().reset_index(name="TOTAL").sort_values(col_mes)

# Top 5 ciudades más violentas (X93-X95, Y22-Y24) y/o homicidio
is_x = df['COD4'].str.match(r'X9[3-5].*', na=False)
is_y = df['COD4'].str.match(r'Y2[2-4].*', na=False)
is_h = df[col_manera].astype(str).str.contains('Homicid', case=False, na=False)
mask_violent = is_x | is_y | is_h

top5_violentas = (
    df.loc[mask_violent]
      .groupby([divi_dep, divi_mun], dropna=False)
      .size().reset_index(name='TOTAL')
      .sort_values('TOTAL', ascending=False)
      .head(5)
)


# === Estandarizar códigos CIE-10 a 4 caracteres y construir catálogo ===
df["COD4"] = df[col_cod_cie].astype(str).str.strip().str[:4].str.upper()
codigos["COD4"] = codigos[cod_code4].astype(str).str.strip().str[:4].str.upper()
catalog = codigos[["COD4", cod_desc4]].drop_duplicates()
catalog.columns = ["COD4", "DESC_COD4"]

top5_violentas = (
    df.loc[mask_violent]
      .groupby([divi_dep, divi_mun], dropna=False)
      .size().reset_index(name="TOTAL")
      .sort_values("TOTAL", ascending=False)
      .head(5)
)

# 10 ciudades con menor mortalidad (>0)
ciudades_tot = (
    df.groupby([divi_dep, divi_mun], dropna=False)
      .size().reset_index(name="TOTAL")
)
ciudades_min10 = ciudades_tot[ciudades_tot["TOTAL"] > 0].sort_values("TOTAL", ascending=True).head(10)

# Top 10 causas (código 4 + desc)
top10_causas = (
    df.groupby(["COD4","DESC_COD4"], dropna=False)
      .size().reset_index(name="TOTAL")
      .sort_values("TOTAL", ascending=False)
      .head(10)
)

# Muertes por sexo por departamento
sexo_dep = (
    df.groupby([divi_dep, "SEXO_NOMBRE"], dropna=False)
      .size().reset_index(name="TOTAL")
)

# Histograma por grupo de edad
edad_dist = (
    df["EDAD_CATEGORIA"].value_counts().rename_axis("EDAD_CATEGORIA").reset_index(name="TOTAL")
)

# ====== App ======
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("Aplicación web interactiva para el análisis de mortalidad en Colombia - 2019 APP WEB "),
    html.P("Exploración de datos de mortalidad no fetal para 2019."),

    # --- Controles globales sencillos ---
    html.Div([
        html.Div([
            html.Label("Filtrar por sexo:"),
            dcc.Dropdown(options=[{"label": s, "value": s} for s in sorted(df["SEXO_NOMBRE"].unique())],
                         value=[], multi=True, id="flt-sexo", placeholder="Todos")
        ], style={"width":"24%", "display":"inline-block", "marginRight":"1%"}),
        html.Div([
            html.Label("Filtrar por departamento:"),
            dcc.Dropdown(options=[{"label": d, "value": d} for d in sorted(df[divi_dep].dropna().unique())],
                         value=[], multi=True, id="flt-dep", placeholder="Todos")
        ], style={"width":"35%", "display":"inline-block"}),
    ], style={"marginBottom":"1rem"}),

    dcc.Tabs([
        dcc.Tab(label="Distribución total de muertes por departamento en Colombia para el año 2019.", children=[
            dcc.Graph(id="fig-mapa")
        ]),
        dcc.Tab(label="Variación mensual 2019", children=[
            dcc.Graph(id="fig-linea")
        ]),
        dcc.Tab(label="Top 5 de Ciudades más violentas de Colombia", children=[
            dcc.Graph(id="fig-violentas")
        ]),
        dcc.Tab(label="Top 10 Ciudades con menor mortalidad de Colombia", children=[
            dcc.Graph(id="fig-minimas")
        ]),
        dcc.Tab(label=" Listado de las 10 principales causas de muerte en Colombia", children=[
            dash_table.DataTable(
                id="tbl-causas",
                columns=[
                    {"name": "Código (4)", "id": "COD4"},
                    {"name": "Descripción", "id": "DESC_COD4"},
                    {"name": "Total", "id": "TOTAL", "type":"numeric", "format": {"specifier": ",d"}},
                ],
                data=top10_causas.to_dict("records"),
                sort_action="native",
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign":"left", "padding":"8px"},
                style_header={"fontWeight": "bold"},
            )
        ]),
        dcc.Tab(label="Comparación del total de muertes por sexo en cada departamento", children=[
            dcc.Graph(id="fig-sexo-dep")
        ]),
        dcc.Tab(label="Distribución de muertes por grupos de edad", children=[
            dcc.Graph(id="fig-edad")
        ]),
    ]),
    html.Div(id="footnote", children=[
        html.Small("Visualización realizada por Cristian Andres Cano - 1036673599 - Maestria Inteligencia Artificial"
                   "Los códigos de violencia consideran X93–X95 y Y22–Y24, además de registros con 'Homicidio' en MANERA_MUERTE.")
    ], style={"marginTop":"1rem"})
])

def apply_filters(df_in, selected_sexo, selected_dep):
    dff = df_in.copy()
    if selected_sexo:
        dff = dff[dff["SEXO_NOMBRE"].isin(selected_sexo)]
    if selected_dep:
        dff = dff[dff[divi_dep].isin(selected_dep)]
    return dff

@app.callback(
    Output("fig-mapa","figure"),
    Output("fig-linea","figure"),
    Output("fig-violentas","figure"),
    Output("fig-minimas","figure"),
    Output("fig-sexo-dep","figure"),
    Output("fig-edad","figure"),
    Input("flt-sexo","value"),
    Input("flt-dep","value"),
)
def update_figs(f_sexo, f_dep):
    # Aplicar filtros
    dff = apply_filters(df, f_sexo, f_dep)

    # 1) MAPA
    try:
        dep_tot_f = (
            dff.groupby([col_cod_dep, divi_dep], dropna=False)
              .size().reset_index(name="TOTAL")
        )
        # Adjuntar coordenadas
        import json, pandas as pd, plotly.express as px
        with open(CENTROIDS_PATH, "r", encoding="utf-8") as f:
            centroids = json.load(f)

        points = []
        for _, row in dep_tot_f.iterrows():
            code = int(row[col_cod_dep]) if pd.notna(row[col_cod_dep]) else None
            c = centroids.get(str(code)) or centroids.get(code)
            if c:
                points.append({"DEPARTAMENTO": row[divi_dep], "TOTAL": int(row["TOTAL"]), "lat": c["lat"], "lon": c["lon"]})
        dep_geo_f = pd.DataFrame(points)

        if dep_geo_f.empty:
            fig_mapa = blank_fig("Total de muertes por departamento (2019)")
        else:
            fig_mapa = px.scatter_geo(dep_geo_f, lat="lat", lon="lon", size="TOTAL",
                                      hover_name="DEPARTAMENTO", projection="natural earth",
                                      title="Total de muertes por departamento (2019)")
            fig_mapa.update_geos(fitbounds="locations", showcountries=True, scope="south america")
            fig_mapa.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    except Exception:
        fig_mapa = blank_fig("Total de muertes por departamento (2019)")

    # 2) SERIE MENSUAL
    try:
        serie_mes_f = dff.groupby(col_mes).size().reset_index(name="TOTAL").sort_values(col_mes)
        if serie_mes_f.empty:
            fig_linea = blank_fig("Total de muertes por mes (2019)")
        else:
            fig_linea = px.line(serie_mes_f, x=col_mes, y="TOTAL", markers=True,
                                labels={col_mes: "Mes", "TOTAL": "Total muertes"},
                                title="Total de muertes por mes (2019)")
            fig_linea.update_xaxes(dtick=1)
    except Exception:
        fig_linea = blank_fig("Total de muertes por mes (2019)")

    # 3) TOP 5 CIUDADES VIOLENTAS
    try:
        is_x = dff["COD4"].str.match(r"X9[3-5].*", na=False)
        is_y = dff["COD4"].str.match(r"Y2[2-4].*", na=False)
        is_h = dff[col_manera].astype(str).str.contains("Homicid", case=False, na=False)
        mask_violent = is_x | is_y | is_h
        top5_v = (
            dff.loc[mask_violent]
               .groupby([divi_dep, divi_mun], dropna=False)
               .size().reset_index(name="TOTAL")
               .sort_values("TOTAL", ascending=False)
               .head(5)
        )
        if top5_v.empty:
            fig_violentas = blank_fig("Top 5 ciudades más violentas")
        else:
            top5_v["CIUDAD"] = top5_v[divi_mun].fillna("Sin municipio") + " (" + top5_v[divi_dep].fillna("Sin depto") + ")"
            fig_violentas = px.bar(top5_v, x="CIUDAD", y="TOTAL",
                                   title="Top 5 ciudades más violentas (X93–X95, Y22–Y24 y Homicidio)")
            fig_violentas.update_layout(xaxis_title="", yaxis_title="Total")
    except Exception:
        fig_violentas = blank_fig("Top 5 ciudades más violentas")

    # 4) 10 CIUDADES CON MENOR MORTALIDAD (>0)
    try:
        ciudades_tot_f = dff.groupby([divi_dep, divi_mun], dropna=False).size().reset_index(name="TOTAL")
        min10 = ciudades_tot_f[ciudades_tot_f["TOTAL"] > 0].sort_values("TOTAL", ascending=True).head(10)
        if min10.empty:
            fig_minimas = blank_fig("10 ciudades con menor mortalidad (>0)")
        else:
            min10["CIUDAD"] = min10[divi_mun].fillna("Sin municipio") + " (" + min10[divi_dep].fillna("Sin depto") + ")"
            fig_minimas = px.pie(min10, names="CIUDAD", values="TOTAL", title="10 ciudades con menor mortalidad (>0)")
    except Exception:
        fig_minimas = blank_fig("10 ciudades con menor mortalidad (>0)")

    # 5) SEXO POR DEPARTAMENTO
    try:
        sexo_dep_f = dff.groupby([divi_dep, "SEXO_NOMBRE"], dropna=False).size().reset_index(name="TOTAL")
        if sexo_dep_f.empty:
            fig_sexo_dep = blank_fig("Muertes por sexo y departamento")
        else:
            fig_sexo_dep = px.bar(sexo_dep_f, x=divi_dep, y="TOTAL", color="SEXO_NOMBRE", barmode="stack",
                                  title="Muertes por sexo y departamento")
            fig_sexo_dep.update_layout(xaxis_title="Departamento", yaxis_title="Total", xaxis={'categoryorder':'total descending'})
    except Exception:
        fig_sexo_dep = blank_fig("Muertes por sexo y departamento")

    # 6) HISTOGRAMA GRUPOS DE EDAD (AGREGADOS)
    try:
        if dff.empty:
            fig_edad = blank_fig("Distribución por grupos de edad (agrupación oficial)")
        else:
            fig_edad = px.histogram(dff, x="EDAD_CATEGORIA", title="Distribución por grupos de edad (agrupación oficial)")
            fig_edad.update_xaxes(categoryorder="array", categoryarray=ordered_age_categories)
    except Exception:
        fig_edad = blank_fig("Distribución por grupos de edad (agrupación oficial)")

    return fig_mapa, fig_linea, fig_violentas, fig_minimas, fig_sexo_dep, fig_edad

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=True)
