// components/Dashboard.jsx
// Dashboard analítico completo para Lambda Analytics.
// Stack: React 18 + Recharts + diseño industrial/utilitario.

import { useState, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { useProyectos, useDashboardResumen } from "../hooks/useProyectos";

// ─── Paleta de colores ────────────────────────────────────────────────────────
const COLORS = {
  primary: "#00D4AA",
  warning: "#F59E0B",
  danger: "#EF4444",
  neutral: "#6B7280",
  bg: "#0F1117",
  surface: "#1A1D26",
  border: "#2D3142",
  text: "#E8EAED",
  muted: "#9AA0B4",
};

const ESTADO_COLOR = {
  activo: COLORS.primary,
  completado: "#60A5FA",
  pausado: COLORS.warning,
  cancelado: COLORS.danger,
};

// ─── Utilidades ───────────────────────────────────────────────────────────────
const fmtMoneda = (v) =>
  new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(v);

const fmtPct = (v) => `${Number(v).toFixed(1)}%`;

// ─── Componentes auxiliares ───────────────────────────────────────────────────

/** Tarjeta de KPI */
const KpiCard = ({ label, value, sub, color = COLORS.primary, icon }) => (
  <div style={{
    background: COLORS.surface,
    border: `1px solid ${COLORS.border}`,
    borderLeft: `3px solid ${color}`,
    borderRadius: 6,
    padding: "20px 24px",
    display: "flex",
    flexDirection: "column",
    gap: 6,
  }}>
    <span style={{ fontSize: 11, letterSpacing: 2, color: COLORS.muted, textTransform: "uppercase" }}>
      {icon} {label}
    </span>
    <span style={{ fontSize: 28, fontWeight: 700, color: COLORS.text, lineHeight: 1 }}>{value}</span>
    {sub && <span style={{ fontSize: 12, color: COLORS.muted }}>{sub}</span>}
  </div>
);

/** Barra de avance */
const ProgressBar = ({ value, color }) => (
  <div style={{ background: COLORS.border, borderRadius: 3, height: 6, width: "100%", overflow: "hidden" }}>
    <div style={{
      width: `${Math.min(value, 100)}%`,
      height: "100%",
      background: color ?? (value >= 70 ? COLORS.primary : value >= 40 ? COLORS.warning : COLORS.danger),
      borderRadius: 3,
      transition: "width 0.4s ease",
    }} />
  </div>
);

/** Badge de estado */
const EstadoBadge = ({ estado }) => (
  <span style={{
    background: `${ESTADO_COLOR[estado] ?? COLORS.neutral}22`,
    color: ESTADO_COLOR[estado] ?? COLORS.neutral,
    border: `1px solid ${ESTADO_COLOR[estado] ?? COLORS.neutral}55`,
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 600,
    padding: "2px 8px",
    textTransform: "uppercase",
    letterSpacing: 1,
  }}>
    {estado}
  </span>
);

/** Skeleton de carga */
const Skeleton = ({ w = "100%", h = 20 }) => (
  <div style={{
    width: w, height: h,
    background: `linear-gradient(90deg, ${COLORS.surface} 25%, ${COLORS.border} 50%, ${COLORS.surface} 75%)`,
    backgroundSize: "200% 100%",
    borderRadius: 4,
    animation: "shimmer 1.4s infinite",
  }} />
);

/** Estado vacío */
const EmptyState = ({ mensaje }) => (
  <div style={{ textAlign: "center", padding: 48, color: COLORS.muted }}>
    <div style={{ fontSize: 32, marginBottom: 12 }}>📭</div>
    <p style={{ margin: 0 }}>{mensaje}</p>
  </div>
);

/** Estado de error */
const ErrorState = ({ mensaje, onRetry }) => (
  <div style={{
    background: `${COLORS.danger}15`,
    border: `1px solid ${COLORS.danger}44`,
    borderRadius: 6,
    padding: 16,
    color: COLORS.danger,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  }}>
    <span>⚠️ {mensaje}</span>
    {onRetry && (
      <button onClick={onRetry} style={{
        background: COLORS.danger, color: "#fff",
        border: "none", borderRadius: 4,
        padding: "6px 14px", cursor: "pointer", fontSize: 12,
      }}>
        Reintentar
      </button>
    )}
  </div>
);

// ─── Sección de KPIs globales ─────────────────────────────────────────────────
const SeccionKpis = ({ resumen, loading, error, onRetry }) => {
  if (error) return <ErrorState mensaje={error} onRetry={onRetry} />;
  if (loading || !resumen) return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
      {[...Array(4)].map((_, i) => <Skeleton key={i} h={90} />)}
    </div>
  );

  const { total_proyectos_activos, promedio_avance, indicadores_criticos, total_actividades_vencidas } = resumen;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
      <KpiCard label="Proyectos activos" value={total_proyectos_activos} icon="🏗️" />
      <KpiCard label="Avance promedio" value={fmtPct(promedio_avance)} icon="📈" color="#60A5FA" />
      <KpiCard
        label="Indicadores críticos"
        value={indicadores_criticos?.length ?? 0}
        icon="🚨"
        color={indicadores_criticos?.length > 0 ? COLORS.danger : COLORS.primary}
      />
      <KpiCard
        label="Actividades vencidas"
        value={total_actividades_vencidas}
        icon="⏰"
        color={total_actividades_vencidas > 0 ? COLORS.warning : COLORS.primary}
      />
    </div>
  );
};

// ─── Gráfico de rendimiento ───────────────────────────────────────────────────
const GraficoRendimiento = ({ proyectos }) => {
  const data = proyectos.slice(0, 8).map((p) => ({
    nombre: p.nombre.length > 14 ? p.nombre.slice(0, 14) + "…" : p.nombre,
    avance: p.avance_porcentaje,
  }));

  return (
    <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 6, padding: 20 }}>
      <h3 style={{ margin: "0 0 16px", fontSize: 13, color: COLORS.muted, textTransform: "uppercase", letterSpacing: 2 }}>
        Avance por Proyecto
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
          <XAxis
            dataKey="nombre"
            tick={{ fill: COLORS.muted, fontSize: 10 }}
            angle={-35}
            textAnchor="end"
          />
          <YAxis tick={{ fill: COLORS.muted, fontSize: 10 }} domain={[0, 100]} />
          <Tooltip
            contentStyle={{ background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 4 }}
            labelStyle={{ color: COLORS.text }}
            formatter={(v) => [`${v}%`, "Avance"]}
          />
          <Bar dataKey="avance" radius={[3, 3, 0, 0]}>
            {data.map((entry, idx) => (
              <Cell
                key={idx}
                fill={entry.avance >= 70 ? COLORS.primary : entry.avance >= 40 ? COLORS.warning : COLORS.danger}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ─── Tabla de proyectos ───────────────────────────────────────────────────────
const COLUMNAS = [
  { key: "nombre",             label: "Proyecto",    sortable: true },
  { key: "cliente",            label: "Cliente",     sortable: false },
  { key: "estado",             label: "Estado",      sortable: true },
  { key: "avance_porcentaje",  label: "Avance",      sortable: true },
  { key: "dias_restantes",     label: "Días rest.",  sortable: false },
];

const TablaProyectos = ({ proyectos, total, loading, error, filtros, onFiltrar, onOrdenar, onPaginar, onRefetch }) => {
  const totalPaginas = Math.ceil(total / (filtros.page_size ?? 10));

  const thStyle = (key) => ({
    padding: "10px 14px",
    textAlign: "left",
    fontSize: 11,
    letterSpacing: 1.5,
    color: COLORS.muted,
    textTransform: "uppercase",
    borderBottom: `1px solid ${COLORS.border}`,
    cursor: "pointer",
    userSelect: "none",
    whiteSpace: "nowrap",
  });

  const tdStyle = {
    padding: "12px 14px",
    borderBottom: `1px solid ${COLORS.border}22`,
    fontSize: 13,
    color: COLORS.text,
    verticalAlign: "middle",
  };

  return (
    <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 6 }}>
      {/* Barra de filtros */}
      <div style={{
        padding: "14px 16px",
        borderBottom: `1px solid ${COLORS.border}`,
        display: "flex",
        gap: 10,
        flexWrap: "wrap",
        alignItems: "center",
      }}>
        <input
          type="text"
          placeholder="Buscar proyecto o cliente…"
          defaultValue={filtros.search ?? ""}
          onChange={(e) => onFiltrar({ search: e.target.value })}
          style={{
            background: COLORS.bg,
            border: `1px solid ${COLORS.border}`,
            color: COLORS.text,
            borderRadius: 4,
            padding: "7px 12px",
            fontSize: 13,
            flex: "1 1 200px",
            minWidth: 140,
          }}
        />
        <select
          value={filtros.estado ?? ""}
          onChange={(e) => onFiltrar({ estado: e.target.value })}
          style={{
            background: COLORS.bg,
            border: `1px solid ${COLORS.border}`,
            color: COLORS.text,
            borderRadius: 4,
            padding: "7px 10px",
            fontSize: 13,
          }}
        >
          <option value="">Todos los estados</option>
          <option value="activo">Activo</option>
          <option value="pausado">Pausado</option>
          <option value="completado">Completado</option>
          <option value="cancelado">Cancelado</option>
        </select>
        <button
          onClick={onRefetch}
          style={{
            background: "transparent",
            border: `1px solid ${COLORS.border}`,
            color: COLORS.muted,
            borderRadius: 4,
            padding: "7px 12px",
            cursor: "pointer",
            fontSize: 13,
          }}
          title="Recargar"
        >
          ↻
        </button>
      </div>

      {/* Tabla */}
      {error ? (
        <div style={{ padding: 16 }}><ErrorState mensaje={error} onRetry={onRefetch} /></div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {COLUMNAS.map((col) => (
                  <th
                    key={col.key}
                    style={thStyle(col.key)}
                    onClick={() => col.sortable && onOrdenar(col.key)}
                  >
                    {col.label}
                    {col.sortable && (
                      <span style={{ marginLeft: 4, opacity: 0.5 }}>
                        {filtros.ordering === col.key ? "↑" : filtros.ordering === `-${col.key}` ? "↓" : "⇅"}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i}>
                    {COLUMNAS.map((col) => (
                      <td key={col.key} style={tdStyle}><Skeleton /></td>
                    ))}
                  </tr>
                ))
              ) : proyectos.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNAS.length}>
                    <EmptyState mensaje="No se encontraron proyectos con los filtros aplicados." />
                  </td>
                </tr>
              ) : (
                proyectos.map((p) => (
                  <tr key={p.id} style={{ transition: "background 0.15s" }}
                    onMouseEnter={(e) => e.currentTarget.style.background = `${COLORS.border}44`}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <td style={{ ...tdStyle, fontWeight: 600 }}>{p.nombre}</td>
                    <td style={{ ...tdStyle, color: COLORS.muted }}>{p.cliente}</td>
                    <td style={tdStyle}><EstadoBadge estado={p.estado} /></td>
                    <td style={{ ...tdStyle, minWidth: 120 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <ProgressBar value={p.avance_porcentaje} />
                        <span style={{ fontSize: 12, color: COLORS.muted, whiteSpace: "nowrap" }}>
                          {fmtPct(p.avance_porcentaje)}
                        </span>
                      </div>
                    </td>
                    <td style={{ ...tdStyle, color: p.dias_restantes < 0 ? COLORS.danger : COLORS.muted }}>
                      {p.dias_restantes < 0 ? `${Math.abs(p.dias_restantes)}d vencido` : `${p.dias_restantes}d`}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Paginación */}
      {!loading && !error && totalPaginas > 1 && (
        <div style={{
          padding: "12px 16px",
          borderTop: `1px solid ${COLORS.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
          fontSize: 12,
          color: COLORS.muted,
        }}>
          <span>{total} proyectos · Página {filtros.page} de {totalPaginas}</span>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              disabled={filtros.page <= 1}
              onClick={() => onPaginar(filtros.page - 1)}
              style={{
                background: COLORS.bg,
                border: `1px solid ${COLORS.border}`,
                color: filtros.page <= 1 ? COLORS.border : COLORS.text,
                borderRadius: 4,
                padding: "4px 10px",
                cursor: filtros.page <= 1 ? "not-allowed" : "pointer",
              }}
            >
              ←
            </button>
            <button
              disabled={filtros.page >= totalPaginas}
              onClick={() => onPaginar(filtros.page + 1)}
              style={{
                background: COLORS.bg,
                border: `1px solid ${COLORS.border}`,
                color: filtros.page >= totalPaginas ? COLORS.border : COLORS.text,
                borderRadius: 4,
                padding: "4px 10px",
                cursor: filtros.page >= totalPaginas ? "not-allowed" : "pointer",
              }}
            >
              →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Dashboard principal ──────────────────────────────────────────────────────
const Dashboard = () => {
  const { resumen, loading: resumenLoading, error: resumenError, refetch: refetchResumen } = useDashboardResumen();
  const { proyectos, total, loading, error, filtros, refetch, filtrar, ordenar, irAPagina } = useProyectos();

  return (
    <div style={{
      minHeight: "100vh",
      background: COLORS.bg,
      color: COLORS.text,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      padding: "0 0 48px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');
        * { box-sizing: border-box; }
        input::placeholder { color: #6B7280; }
        select option { background: #1A1D26; }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @media (max-width: 640px) {
          .dashboard-header { padding: 16px !important; }
          .dashboard-body { padding: 12px !important; }
        }
      `}</style>

      {/* Header */}
      <header style={{
        borderBottom: `1px solid ${COLORS.border}`,
        padding: "16px 28px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        position: "sticky",
        top: 0,
        background: `${COLORS.bg}ee`,
        backdropFilter: "blur(8px)",
        zIndex: 10,
      }} className="dashboard-header">
        <div>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: COLORS.primary, letterSpacing: 2 }}>
            LAMBDA ANALYTICS
          </h1>
          <p style={{ margin: 0, fontSize: 11, color: COLORS.muted, letterSpacing: 1 }}>
            DASHBOARD · CONSTRUCCIÓN
          </p>
        </div>
        <div style={{ fontSize: 11, color: COLORS.muted }}>
          {new Date().toLocaleDateString("es-CO", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).toUpperCase()}
        </div>
      </header>

      {/* Cuerpo */}
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 20 }} className="dashboard-body">

        {/* KPIs */}
        <section>
          <h2 style={{ fontSize: 11, color: COLORS.muted, letterSpacing: 2, textTransform: "uppercase", margin: "0 0 12px" }}>
            Resumen Global
          </h2>
          <SeccionKpis resumen={resumen} loading={resumenLoading} error={resumenError} onRetry={refetchResumen} />
        </section>

        {/* Gráfico */}
        {!loading && proyectos.length > 0 && (
          <GraficoRendimiento proyectos={proyectos} />
        )}

        {/* Tabla */}
        <section>
          <h2 style={{ fontSize: 11, color: COLORS.muted, letterSpacing: 2, textTransform: "uppercase", margin: "0 0 12px" }}>
            Proyectos · {total} registros
          </h2>
          <TablaProyectos
            proyectos={proyectos}
            total={total}
            loading={loading}
            error={error}
            filtros={filtros}
            onFiltrar={filtrar}
            onOrdenar={ordenar}
            onPaginar={irAPagina}
            onRefetch={refetch}
          />
        </section>

        {/* Indicadores críticos */}
        {resumen?.indicadores_criticos?.length > 0 && (
          <section>
            <h2 style={{ fontSize: 11, color: COLORS.danger, letterSpacing: 2, textTransform: "uppercase", margin: "0 0 12px" }}>
              ⚠ Indicadores Críticos
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
              {resumen.indicadores_criticos.map((ind) => (
                <div key={ind.id} style={{
                  background: COLORS.surface,
                  border: `1px solid ${COLORS.danger}44`,
                  borderLeft: `3px solid ${COLORS.danger}`,
                  borderRadius: 6,
                  padding: "14px 18px",
                }}>
                  <p style={{ margin: "0 0 4px", fontWeight: 700, fontSize: 13, color: COLORS.text }}>{ind.nombre}</p>
                  <p style={{ margin: "0 0 8px", fontSize: 11, color: COLORS.muted }}>{ind.proyecto_nombre}</p>
                  <ProgressBar value={ind.rendimiento_porcentaje} color={COLORS.danger} />
                  <p style={{ margin: "6px 0 0", fontSize: 11, color: COLORS.danger }}>
                    {fmtPct(ind.rendimiento_porcentaje)} de {ind.valor_objetivo}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
