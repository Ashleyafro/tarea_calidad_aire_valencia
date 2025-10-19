import requests 
import pandas as pd
from sqlalchemy import create_engine 
import os
import argparse
import matplotlib.pyplot as plt
from pathlib import Path
from docx import Document

    
def check_updates(data, engine):
    # Convertir API en DataFrame
    df_api = pd.DataFrame(data["results"])
    df_api["fecha_carg"] = pd.to_datetime(df_api["fecha_carg"])

    # agarramos la fecha más reciente de nuestra base de datos
    latest_db_fecha = "SELECT MAX(fecha_carg) as latest_fecha FROM tabla_bd"

    # Obtener la fecha max de los datos recolectados de la API
    latest_api_fecha = df_api["fecha_carg"].max()

    # Check si los datos que tenemos están actualizados
    if latest_api_fecha != latest_db_fecha:
        print("Nuevos datos guardados")
        # get latest df
        registro_path = "./output/historico/registro_historico.csv"
        tabla_actualizada = df_api.to_sql("tabla_bd", con = engine, if_exists = 'append', index = False)
        tabla_actualizada.to_csv(registro_path, index=False)
        #save_raw_csv(last_df.to_dict(orient="records"), engine)    ?
    else:
        print("No hay nuevos records")
        return None

def save_raw_csv(data, engine):
    # conseguir datos
    df = pd.DataFrame(data["results"])
    cleaned_df = pd.DataFrame(df[["objectid", "nombre", "direccion", "tipozona", "no2", "pm10", "pm25", "tipoemisio", "fecha_carg", "calidad_am", "fiwareid"]])
    cleaned_df = cleaned_df[cleaned_df.objectid != 22]
    cleaned_df["fecha_carg"] = pd.to_datetime(cleaned_df["fecha_carg"], format="%Y-%m-%dT%H:%M:%S%z")

    # Save in PostgreSQL
    cleaned_df.to_sql("tabla_bd", engine, if_exists="replace", index=False)
    print("Datos cargados a PostgreSQL")
    
    # Guardar el CSV
    os.makedirs("./data/raw", exist_ok=True)
    latest_date = cleaned_df["fecha_carg"].max() 
    cleaned_df["fecha_carg"] = cleaned_df["fecha_carg"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    safe_timestamp = latest_date.strftime("%Y-%m-%dT%H-%M-%S")
    csv_filepath = os.path.join("./data/raw", f"ultimo_{safe_timestamp}.csv")

    try:
            cleaned_df.to_csv(csv_filepath, index=False)
            print(f"CSV guardado en: {csv_filepath}")
    except:
            print(f"Error al guardar el archivo CSV")

    # get path for registro
    file = "./output/historico/registro_historico.csv"
    if (os.path.exists(file) and os.path.isfile(file)):
        os.remove(file)
        #registro_path = "./output/historico/registro_historico.csv "?
        registro_df = pd.read_sql("SELECT * FROM tabla_bd", engine)
        #registro_df.to_csv(registro_path, index=False)  ?
        registro_df.to_csv(file, index=False)
    else:
        registro_df = pd.read_sql("SELECT * FROM tabla_bd", engine)
        registro_df.to_csv(file, index=False)

def parse_args():
    #Creamos el parser (p) para parsear argumentos 
    p = argparse.ArgumentParser(description="Reportes")
    #Añadimos los argumemtos:
    p.add_argument("--modo", choices=["actual", "historico"], required=True, help="Modo: 'actual' o 'historico'")   #Argumento modo en donde tienes que elegir entre actual o historico
    p.add_argument("--since", type=str, help="Fecha de inicio (formato: YYYY-MM-DD)") #Argumento que recibe una cadena string de fecha
    p.add_argument("--estacion", type=str, help="ID de estacion")   #Argumento para filtrar segun el fiwareid
    return p.parse_args()

def generate_actual_report():
    # Obtener el último CSV
    csv_folder = "./data/raw/"
    last_file = os.listdir(csv_folder)[0]    #Obtiene el primer nombre del archivo que se encuentra dentro de la carpeta (ruta)
    if not last_file:   #Caso en donde no hayan archivos en esa ruta
        print("No hay CSV")  
    else:
        latest_csv = os.path.join(csv_folder, last_file)
        df_latest = pd.read_csv(latest_csv)     #Pasamos el último csv como un df llamado df_latest

        #Cálculo de valores
        summary = df_latest.groupby("fiwareid")[["no2", "pm10", "pm25"]].sum()
        
        os.makedirs("./output/actual", exist_ok=True)
        print("Tabla de resumen guardada")

        #Creación de gráficas
        summary["no2"].plot(kind="bar", title="Gráfico de barras no2 por estación", color = "red")
        plt.xlabel("Estacion")
        plt.ylabel("Nivel NO2") 

        summary["pm10"].plot(kind="bar", title="Gráfico de barras no2 por estación", color = "red")
        plt.xlabel("Estacion")
        plt.ylabel("Nivel pm10")

        summary["pm25"].plot(kind="bar", title="Gráfico de barras no2 por estación", color = "red")
        plt.xlabel("Estacion")
        plt.ylabel("Nivel pm25")

        #Exportamos gráficas
        output_dir = os.path.join("./output/actual")
        os.makedirs(output_dir, exist_ok=True)

        summary.to_csv(os.path.join(output_dir, "tabla_actual.csv"))

        plt.savefig(os.path.join(output_dir, "no2_por_estacion.png"))
        plt.savefig(os.path.join(output_dir, "pm10_por_estacion.png"))
        plt.savefig(os.path.join(output_dir, "pm25_por_estacion.png"))
        #Guardamos las gráficas en un doc
        doc = Document()
        doc.add_heading('Grafica informe actual estacion/no2', level=1)
        doc.add_paragraph('Informe actual sobre el No2 generado según la estación')
        doc.add_picture("./output/actual/no2_por_estacion.png")
        doc.add_heading('Grafica informe actual estacion/pm10', level=1)
        doc.add_paragraph('Informe actual sobre el pm10 generado según la estación')
        doc.add_picture("./output/actual/pm10_por_estacion.png" )
        doc.add_heading('Grafica informe actual estacion/pm25', level=1)
        doc.add_paragraph('Informe actual sobre el pm25 generado según la estación')
        doc.add_picture("./output/actual/pm25_por_estacion.png")

        save_path = os.path.join(output_dir, "Reporte_Actual.docx")
        doc.save(save_path)

        print("Graficos actuales guardados")

def generate_historico_report(since, estacion):
    #Obtener último csv
    historico_df = pd.read_csv("./output/historico/registro_historico.csv")
    #Filtramos en base a lo que el usuario haya puesto
    if since:
        since_date = pd.to_datetime(since, format="%Y-%m-%d") #pasamos since a una variable de tipo datetime
        historico_df["fecha_carg"] = pd.to_datetime(historico_df["fecha_carg"]) #evitar errores a la hora de comparar fechas (fecha_carg no es tipo datetime)
        historico_df = historico_df[historico_df["fecha_carg"] >= since_date]   #filtramos desde la fecha dada (since_date) hasta la última fecha de carga
        
    if estacion:
        historico_df = historico_df[historico_df["fiwareid"] == estacion]   #filtramos según la estación recibida

    plt.figure(figsize=(10,5))  #tamaño del gráfico (rectangular)
    #Marker muestra un circulo y linestyle une los circulos en una linea contínua
    plt.plot(historico_df["fecha_carg"], historico_df["no2"], marker='o', linestyle='-')    #dibuja gráfica del tiempo en donde "eje x" es la fecha de carga y el "eje y" el no2 generado.

    #Creamos gráfica
    plt.title("NO2 histórico por estación")
    plt.xlabel("Fecha")
    plt.ylabel("Nivel NO2")
    plt.tight_layout()

    #La guardamos
    output_dir = "./output/historico"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "NO2_historico.png"))
    plt.close()
    print("Graficos historicos guardados")

def main():
    args = parse_args()

    #Obtener datos de la API
    url = "https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/estacions-contaminacio-atmosferiques-estaciones-contaminacion-atmosfericas/records"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()  # Diccionario con más de una llave, solo queremos la llave 'results'
        print("Conexión exitosa a la API")
    except:
        print("Error en la conexión")
        return

    #Conexión a POSTGRES
    churro = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres' #Puente de conexión que nos permite leer y escribir tablas en Postgres
    engine = create_engine(churro)


    save_raw_csv(data, engine)
    
    if args.modo == "historico":
        generate_historico_report(args.since, args.estacion)
    elif args.modo == "actual":
        generate_actual_report()

if __name__ == "__main__":
    main()

