import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { useProyectos, useDashboardResumen } from "./useProyectos";

const getColor = (avance) => {
  if (avance >= 70) return "#10b981";
  if (avance >= 40) return "#f59e0b";
  return "#ef4444";
};

const EstadoBadge = ({ estado }) => {
  const colores = {
    activo: "#10b981",
    completado: "#3b82f6",
    pausado: "#f59e0b",
    cancelado: "#ef4444",
  };
  return (
    <span style={{
      background: `${colores[estado]}22`,
      color: colores[estado],
      border: `1px solid ${colores[estado]}`,
      borderRadius: 4,
      fontSize: 11,
      padding: "2px 8px",
    }}>
      {estado}
    </span>
  );
};

const ProgressBar = ({ value }) => (
  <div style={{ background: "#e5e7eb", borderRadius: 3, height: 6, width: "100%" }}>
    <div style={{
      width: `${Math.min(value, 100)}%`,
      height: "100%",
      background: getColor(value),
      borderRadius: 3,
    }} />
  </div>
);

const KpiCard = ({ label, value, color = "#10b981" }) => (
  <div style={{
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderLeft: `3px solid ${color}`,
    borderRadius: 6,
    padding: "16px 20px",
  }}>
    <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>{label}</p>
    <p style={{ margin: "4px 0 0", fontSize: 26, fontWeight: 700, color: "#111827" }}>{value}</p>
  </div>
);

const Dashboard = () => {
  const { proyectos, total, loading, error, filtros, filtrar, ordenar, irAPagina, refetch } = useProyectos();
  const { resumen, loading: resumenLoading } = useDashboardResumen();
  const [busqueda, setBusqueda] = useState("");

  const totalPaginas = Math.ceil(total / (filtros.page_size || 10));

  const handleBusqueda = (e) => {
    setBusqueda(e.target.value);
    filtrar({ search: e.target.value });
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f9fafb", fontFamily: "sans-serif" }}>

      {/* Header */}
      <div style={{ background: "#fff", borderBottom: "1px solid #e5e7eb", padding: "14px 24px" }}>
        <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#111827" }}>
          Dashboard — Lambda Analytics
        </h1>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>

        {/* KPIs */}
        {!resumenLoading && resumen && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
            <KpiCard label="Proyectos activos" value={resumen.total_proyectos_activos} />
            <KpiCard label="Avance promedio" value={`${resumen.promedio_avance}%`} color="#3b82f6" />
            <KpiCard
              label="Indicadores críticos"
              value={resumen.indicadores_criticos?.length || 0}
              color={resumen.indicadores_criticos?.length > 0 ? "#ef4444" : "#10b981"}
            />
            <KpiCard
              label="Actividades vencidas"
              value={resumen.actividades_vencidas || 0}
              color={resumen.actividades_vencidas > 0 ? "#f59e0b" : "#10b981"}
            />
          </div>
        )}

        {/* Grafico */}
        {!loading && proyectos.length > 0 && (
          <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 6, padding: 20, marginBottom: 24 }}>
            <p style={{ margin: "0 0 16px", fontSize: 13, fontWeight: 600, color: "#374151" }}>
              Avance por proyecto
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={proyectos.slice(0, 8).map(p => ({ nombre: p.nombre.slice(0, 12), avance: p.avance_porcentaje }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="nombre" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [`${v}%`, "Avance"]} />
                <Bar dataKey="avance" radius={[3, 3, 0, 0]}>
                  {proyectos.slice(0, 8).map((p, i) => (
                    <Cell key={i} fill={getColor(p.avance_porcentaje)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Tabla */}
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 6 }}>

          {/* Filtros */}
          <div style={{ padding: "12px 16px", borderBottom: "1px solid #e5e7eb", display: "flex", gap: 10 }}>
            <input
              type="text"
              placeholder="Buscar proyecto..."
              value={busqueda}
              onChange={handleBusqueda}
              style={{ border: "1px solid #e5e7eb", borderRadius: 4, padding: "6px 10px", fontSize: 13, flex: 1 }}
            />
            <select
              value={filtros.estado || ""}
              onChange={(e) => filtrar({ estado: e.target.value })}
              style={{ border: "1px solid #e5e7eb", borderRadius: 4, padding: "6px 10px", fontSize: 13 }}
            >
              <option value="">Todos</option>
              <option value="activo">Activo</option>
              <option value="pausado">Pausado</option>
              <option value="completado">Completado</option>
              <option value="cancelado">Cancelado</option>
            </select>
            <button
              onClick={refetch}
              style={{ border: "1px solid #e5e7eb", borderRadius: 4, padding: "6px 12px", fontSize: 13, cursor: "pointer", background: "#fff" }}
            >
              ↻
            </button>
          </div>

          {/* Tabla contenido */}
          {error ? (
            <p style={{ padding: 16, color: "#ef4444" }}>Error: {error}</p>
          ) : loading ? (
            <p style={{ padding: 16, color: "#6b7280" }}>Cargando...</p>
          ) : proyectos.length === 0 ? (
            <p style={{ padding: 16, color: "#6b7280" }}>No se encontraron proyectos</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
                  {["nombre", "cliente", "estado", "avance_porcentaje"].map((col) => (
                    <th
                      key={col}
                      onClick={() => ordenar(col)}
                      style={{ padding: "10px 14px", textAlign: "left", fontSize: 12, color: "#6b7280", cursor: "pointer" }}
                    >
                      {col === "avance_porcentaje" ? "Avance" : col.charAt(0).toUpperCase() + col.slice(1)}
                      {filtros.ordering === col ? " ↑" : filtros.ordering === `-${col}` ? " ↓" : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {proyectos.map((p) => (
                  <tr key={p.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "12px 14px", fontSize: 13, fontWeight: 600 }}>{p.nombre}</td>
                    <td style={{ padding: "12px 14px", fontSize: 13, color: "#6b7280" }}>{p.cliente}</td>
                    <td style={{ padding: "12px 14px" }}><EstadoBadge estado={p.estado} /></td>
                    <td style={{ padding: "12px 14px", minWidth: 140 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <ProgressBar value={p.avance_porcentaje} />
                        <span style={{ fontSize: 12, color: "#6b7280" }}>{p.avance_porcentaje}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {/* Paginacion */}
          {totalPaginas > 1 && (
            <div style={{ padding: "12px 16px", borderTop: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between", fontSize: 12, color: "#6b7280" }}>
              <span>{total} proyectos</span>
              <div style={{ display: "flex", gap: 6 }}>
                <button disabled={filtros.page <= 1} onClick={() => irAPagina(filtros.page - 1)}
                  style={{ padding: "4px 10px", cursor: "pointer", border: "1px solid #e5e7eb", borderRadius: 4 }}>←</button>
                <span style={{ padding: "4px 8px" }}>{filtros.page} / {totalPaginas}</span>
                <button disabled={filtros.page >= totalPaginas} onClick={() => irAPagina(filtros.page + 1)}
                  style={{ padding: "4px 10px", cursor: "pointer", border: "1px solid #e5e7eb", borderRadius: 4 }}>→</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;