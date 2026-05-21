// hooks/useProyectos.js
// Custom hook para manejo de datos de proyectos con caché, filtros y paginación.

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api";
const CACHE_TTL_MS = 60_000; // 1 minuto

// Caché en memoria: { cacheKey → { data, timestamp } }
const cache = new Map();

/**
 * Obtiene el token JWT del localStorage y retorna el header de autorización.
 */
const authHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

/**
 * @typedef {Object} FiltrosProyecto
 * @property {string} [estado]         - "activo" | "pausado" | "completado" | "cancelado"
 * @property {string} [search]         - Búsqueda libre por nombre/cliente
 * @property {string} [ordering]       - Campo de ordenamiento (ej: "-avance_porcentaje")
 * @property {number} [page]           - Número de página
 * @property {number} [page_size]      - Resultados por página
 * @property {number} [avance_min]     - Avance mínimo (0-100)
 * @property {number} [avance_max]     - Avance máximo (0-100)
 */

/**
 * Hook principal para manejo de proyectos.
 *
 * @param {FiltrosProyecto} filtrosIniciales
 * @returns {{
 *   proyectos: Array,
 *   total: number,
 *   loading: boolean,
 *   error: string|null,
 *   filtros: FiltrosProyecto,
 *   refetch: () => void,
 *   filtrar: (nuevosFiltros: FiltrosProyecto) => void,
 *   ordenar: (campo: string) => void,
 *   irAPagina: (pagina: number) => void,
 * }}
 */
export const useProyectos = (filtrosIniciales = {}) => {
  const [proyectos, setProyectos] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtros, setFiltros] = useState({
    page: 1,
    page_size: 10,
    ordering: "-creado_en",
    ...filtrosIniciales,
  });

  // Ref para cancelar requests desactualizados
  const abortRef = useRef(null);

  const fetchProyectos = useCallback(async (currentFiltros) => {
    // Cancelar request previo si aún está en vuelo
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    // Construir query string
    const params = new URLSearchParams();
    Object.entries(currentFiltros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") params.append(k, v);
    });
    const url = `${API_BASE}/proyectos/?${params.toString()}`;

    // Revisar caché
    const cached = cache.get(url);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      setProyectos(cached.data.results);
      setTotal(cached.data.count);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(url, {
        headers: authHeaders(),
        signal: abortRef.current.signal,
      });

      if (res.status === 401) {
        throw new Error("Sesión expirada. Por favor, inicia sesión nuevamente.");
      }
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Error ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      cache.set(url, { data, timestamp: Date.now() });
      setProyectos(data.results ?? []);
      setTotal(data.count ?? 0);
    } catch (err) {
      if (err.name === "AbortError") return; // Request cancelado, no es error
      setError(err.message || "Error al cargar proyectos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProyectos(filtros);
    return () => abortRef.current?.abort();
  }, [filtros, fetchProyectos]);

  /** Fuerza una recarga limpiando el caché. */
  const refetch = useCallback(() => {
    cache.clear();
    fetchProyectos(filtros);
  }, [filtros, fetchProyectos]);

  /** Aplica nuevos filtros y regresa a la página 1. */
  const filtrar = useCallback((nuevosFiltros) => {
    setFiltros((prev) => ({ ...prev, ...nuevosFiltros, page: 1 }));
  }, []);

  /** Cambia el campo de ordenamiento, invirtiendo si ya estaba activo. */
  const ordenar = useCallback((campo) => {
    setFiltros((prev) => {
      const actual = prev.ordering ?? "";
      const nuevo = actual === campo ? `-${campo}` : campo;
      return { ...prev, ordering: nuevo, page: 1 };
    });
  }, []);

  /** Navega a una página específica. */
  const irAPagina = useCallback((pagina) => {
    setFiltros((prev) => ({ ...prev, page: pagina }));
  }, []);

  return { proyectos, total, loading, error, filtros, refetch, filtrar, ordenar, irAPagina };
};


/**
 * Hook para obtener el resumen global del dashboard.
 */
export const useDashboardResumen = () => {
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchResumen = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/dashboard/resumen/`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setResumen(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchResumen();
  }, [fetchResumen]);

  return { resumen, loading, error, refetch: fetchResumen };
};
