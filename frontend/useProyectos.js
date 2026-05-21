import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

const getHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export const useProyectos = (filtrosIniciales = {}) => {
  const [proyectos, setProyectos] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtros, setFiltros] = useState({
    page: 1,
    page_size: 10,
    ...filtrosIniciales,
  });

  const fetchProyectos = useCallback(async () => {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.append(k, v);
    });

    try {
      const res = await fetch(`${API_BASE}/proyectos/?${params}`, {
        headers: getHeaders(),
      });

      if (!res.ok) {
        throw new Error(`Error ${res.status}`);
      }

      const data = await res.json();
      setProyectos(data.results || []);
      setTotal(data.count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => {
    fetchProyectos();
  }, [fetchProyectos]);

  const filtrar = (nuevosFiltros) => {
    setFiltros((prev) => ({ ...prev, ...nuevosFiltros, page: 1 }));
  };

  const ordenar = (campo) => {
    setFiltros((prev) => ({
      ...prev,
      ordering: prev.ordering === campo ? `-${campo}` : campo,
      page: 1,
    }));
  };

  const irAPagina = (pagina) => {
    setFiltros((prev) => ({ ...prev, page: pagina }));
  };

  return {
    proyectos,
    total,
    loading,
    error,
    filtros,
    refetch: fetchProyectos,
    filtrar,
    ordenar,
    irAPagina,
  };
};

export const useDashboardResumen = () => {
  const [resumen, setResumen] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResumen = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/resumen/`, {
          headers: getHeaders(),
        });
        if (!res.ok) throw new Error(`Error ${res.status}`);
        const data = await res.json();
        setResumen(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchResumen();
  }, []);

  return { resumen, loading, error };
};