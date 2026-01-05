"use client";
import { useState } from 'react';

export default function ValidadorMedico() {
  const [sintomas, setSintomas] = useState('');
  const [examen, setExamen] = useState('');
  const [resultado, setResultado] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const consultarIA = async () => {
    if (!sintomas || !examen) {
      alert("Por favor rellena ambos campos");
      return;
    }

    setCargando(true);
    setResultado(null);

    try {
      // Importante: La URL debe ser la de tu servidor FastAPI (8000)
        //const response = await fetch('/api/validar', {
        const response = await fetch('http://127.0.0.1:8000/validar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sintomas, examen }),
      });

      if (!response.ok) throw new Error("Error en la respuesta del servidor");

      const data = await response.json();
      setResultado(data.respuesta);
    } catch (error) {
      console.error(error);
      setResultado("❌ Error: No se pudo conectar con el servidor de Python.");
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col items-center p-6 font-sans">
      <div className="max-w-2xl w-full space-y-8 mt-10">
        <header className="text-center">
          <h1 className="text-4xl font-extrabold text-blue-500 mb-2">Auditor Médico IA</h1>
          <p className="text-gray-400">Validación de pertinencia clínica para Seguros y Pacientes</p>
        </header>

        <section className="bg-gray-900 p-6 rounded-2xl border border-gray-800 shadow-2xl space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-blue-300">Describe tus síntomas:</label>
            <textarea
              className="w-full p-4 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-white transition-all"
              placeholder="Ej: Dolor agudo en la fosa ilíaca derecha, náuseas y fiebre..."
              rows={3}
              value={sintomas}
              onChange={(e) => setSintomas(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 text-blue-300">Examen que se pretende realizar:</label>
            <input
              type="text"
              className="w-full p-4 bg-gray-800 border border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-white transition-all"
              placeholder="Ej: Ecografía abdominal"
              value={examen}
              onChange={(e) => setExamen(e.target.value)}
            />
          </div>

          <button
            onClick={consultarIA}
            disabled={cargando}
            className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
              cargando 
              ? 'bg-gray-700 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-900/20'
            }`}
          >
            {cargando ? "🤖 Razonando..." : "Ejecutar Evaluación"}
          </button>
        </section>

        {resultado && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-gray-800 border-l-4 border-blue-500 p-6 rounded-r-xl shadow-xl">
              <h3 className="text-blue-400 font-bold mb-3 flex items-center">
                <span className="mr-2">📋</span> Resultado del Análisis:
              </h3>
              <div className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                {resultado}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}