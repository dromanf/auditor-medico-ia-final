import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv

# 1. CARGAR CONFIGURACIÓN
load_dotenv()

# Inicializar cliente de Groq con la API Key del archivo .env
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

# 2. CONFIGURAR CORS
# Permite que tu frontend en localhost:3000 se comunique con este backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE RUTAS LOCALES ---
# Define la ruta absoluta para encontrar el CSV en la carpeta backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "clean.csv")

# 3. GESTIÓN DE MEMORIA Y MODELOS DE DATOS
historial_clinico = []

class ConsultaMedica(BaseModel):
    sintomas: str
    examen: str

def obtener_protocolo_csv(nombre_examen_usuario):
    """
    Busca de forma flexible el examen en el archivo clean.csv
    """
    try:
        if not os.path.exists(CSV_PATH):
            print(f"Error: No se encuentra el archivo en {CSV_PATH}")
            return None
            
        df = pd.read_csv(CSV_PATH)
        busqueda = nombre_examen_usuario.lower().strip()
        
        # Filtro flexible para encontrar coincidencias parciales
        filtro = df['Nombre del Examen'].str.lower().str.contains(busqueda, na=False)
        resultado = df[filtro]
        
        if not resultado.empty:
            return resultado.iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"Error procesando el CSV: {e}")
        return None

# 4. RUTA PRINCIPAL DE VALIDACIÓN
@app.post("/validar")
async def validar_consulta(datos: ConsultaMedica):
    try:
        # A. Buscar información en la base de datos local (CSV)
        info_csv = obtener_protocolo_csv(datos.examen)
        
        if info_csv:
            contexto_reglas = f"""
            REGLAS OFICIALES DEL SEGURO (CSV):
            - Examen: {info_csv['Nombre del Examen']}
            - Costo: ${info_csv['Costo']}
            - Especialidad: {info_csv['Especialidad']}
            - Protocolo: {info_csv['Protocolo']}
            """
        else:
            contexto_reglas = "ADVERTENCIA: El examen no está en el catálogo oficial de costos, pero debe evaluarse clínicamente."

        # B. Contexto de Memoria (Para conectar síntomas previos)
        contexto_memoria = ""
        if historial_clinico:
            ultimos = historial_clinico[-3:] # Tomamos los últimos 3 registros
            contexto_memoria = "HISTORIAL RECIENTE DEL PACIENTE:\n" + "\n".join(
                [f"- Síntomas: {h['sintomas']} | Examen: {h['examen']}" for h in ultimos]
            )

        # C. Construcción del Prompt con Enfoque Diagnóstico
        prompt_sistema = f"""
        Eres un Auditor Médico Experto con capacidad de diagnóstico diferencial. 
        Tu trabajo no es solo validar costos, sino evaluar la pertinencia clínica profunda.

        {contexto_reglas}
        
        {contexto_memoria}

        INSTRUCCIONES DE ANÁLISIS:
        1. Evalúa la relación entre síntomas y el examen solicitado.
        2. Realiza una inferencia diagnóstica (qué enfermedades podrían causar estos síntomas).
        3. Si el examen no es el ideal, sugiere cuál sería el 'Gold Standard' médico.

        FORMATO DE RESPUESTA (Estricto):
        ESTADO: [PROCEDENTE, ALERTA o RECHAZADO]
        ANÁLISIS TÉCNICO: (Análisis médico detallado, sospechas diagnósticas y justificación del protocolo)
        PARA EL PACIENTE: (Explicación empática y clara sobre su salud y la necesidad del examen)
        RESUMEN ECONÓMICO: (Menciona costos del CSV y si el gasto está justificado clínicamente)
        """

        prompt_usuario = f"SÍNTOMAS ACTUALES: {datos.sintomas}\nEXAMEN SOLICITADO: {datos.examen}"

        # D. Llamada a la IA (Groq)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.2 # Un poco más de creatividad para el diagnóstico
        )

        respuesta_ia = completion.choices[0].message.content

        # E. Actualizar Memoria para futuras consultas
        historial_clinico.append({"sintomas": datos.sintomas, "examen": datos.examen})

        return {"respuesta": respuesta_ia}

    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))