// Dashboard.test.jsx
// Tests del componente Dashboard con React Testing Library.

import React from "react";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { rest } from "msw";
import { setupServer } from "msw/node";
import Dashboard from "./Dashboard";

// ─── Mock de datos ────────────────────────────────────────────────────────────

const resumenMock = {
  total_proyectos_activos: 3,
  promedio_avance: 47.5,
  top_proyectos: [
    { id: 1, nombre: "Edificio Central", cliente: "ABC", avance_porcentaje: 80, estado: "activo" },
    { id: 2, nombre: "Torre Norte", cliente: "XYZ", avance_porcentaje: 55, estado: "activo" },
  ],
  indicadores_criticos: [
    { id: 1, nombre: "Avance físico", proyecto_nombre: "Edificio Central", valor_actual: 20, valor_objetivo: 100, rendimiento_porcentaje: 20 },
  ],
  total_actividades_vencidas: 2,
  proyectos_por_estado: { activo: 3, completado: 1 },
};

const proyectosMock = {
  count: 2,
  results: [
    {
      id: 1,
      nombre: "Edificio Central",
      cliente: "Constructora ABC",
      estado: "activo",
      avance_porcentaje: 80,
      dias_restantes: 45,
    },
    {
      id: 2,
      nombre: "Torre Norte",
      cliente: "Inversiones XYZ",
      estado: "activo",
      avance_porcentaje: 55,
      dias_restantes: 12,
    },
  ],
};

// ─── MSW Server ───────────────────────────────────────────────────────────────

const server = setupServer(
  rest.get("*/api/dashboard/resumen/", (req, res, ctx) => res(ctx.json(resumenMock))),
  rest.get("*/api/proyectos/", (req, res, ctx) => res(ctx.json(proyectosMock)))
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Dashboard", () => {
  describe("Carga inicial", () => {
    test("muestra el header con el nombre de la empresa", async () => {
      render(<Dashboard />);
      expect(screen.getByText(/LAMBDA ANALYTICS/i)).toBeInTheDocument();
    });

    test("muestra skeleton durante la carga", () => {
      render(<Dashboard />);
      // Los elementos de carga deben estar presentes antes de los datos
      const skeletons = document.querySelectorAll('[style*="shimmer"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    test("muestra los KPIs correctamente", async () => {
      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText("3")).toBeInTheDocument(); // total_proyectos_activos
        expect(screen.getByText("47.5%")).toBeInTheDocument(); // promedio_avance
        expect(screen.getByText("1")).toBeInTheDocument(); // indicadores_criticos
        expect(screen.getByText("2")).toBeInTheDocument(); // actividades_vencidas
      });
    });

    test("muestra proyectos en la tabla", async () => {
      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText("Edificio Central")).toBeInTheDocument();
        expect(screen.getByText("Torre Norte")).toBeInTheDocument();
      });
    });

    test("muestra la sección de indicadores críticos", async () => {
      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText(/Indicadores Críticos/i)).toBeInTheDocument();
        expect(screen.getByText("Avance físico")).toBeInTheDocument();
      });
    });
  });

  describe("Filtros y búsqueda", () => {
    test("permite filtrar por nombre", async () => {
      const user = userEvent.setup();
      let capturedUrl = "";

      server.use(
        rest.get("*/api/proyectos/", (req, res, ctx) => {
          capturedUrl = req.url.toString();
          return res(ctx.json({ count: 1, results: [proyectosMock.results[0]] }));
        })
      );

      render(<Dashboard />);
      await waitFor(() => screen.getByPlaceholderText(/Buscar/i));
      const input = screen.getByPlaceholderText(/Buscar/i);
      await user.type(input, "Edificio");

      await waitFor(() => {
        expect(capturedUrl).toContain("search=Edificio");
      });
    });

    test("permite filtrar por estado", async () => {
      let capturedUrl = "";
      server.use(
        rest.get("*/api/proyectos/", (req, res, ctx) => {
          capturedUrl = req.url.toString();
          return res(ctx.json(proyectosMock));
        })
      );

      render(<Dashboard />);
      await waitFor(() => screen.getByRole("combobox"));
      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "activo" } });

      await waitFor(() => {
        expect(capturedUrl).toContain("estado=activo");
      });
    });
  });

  describe("Manejo de errores", () => {
    test("muestra error si la API falla en proyectos", async () => {
      server.use(
        rest.get("*/api/proyectos/", (req, res, ctx) =>
          res(ctx.status(500), ctx.json({ detail: "Server error" }))
        )
      );

      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText(/Error 500/i)).toBeInTheDocument();
      });
    });

    test("muestra botón de reintento en caso de error", async () => {
      server.use(
        rest.get("*/api/proyectos/", (req, res, ctx) => res(ctx.status(503)))
      );

      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText(/Reintentar/i)).toBeInTheDocument();
      });
    });
  });

  describe("Estado vacío", () => {
    test("muestra estado vacío cuando no hay proyectos", async () => {
      server.use(
        rest.get("*/api/proyectos/", (req, res, ctx) =>
          res(ctx.json({ count: 0, results: [] }))
        )
      );

      render(<Dashboard />);
      await waitFor(() => {
        expect(screen.getByText(/No se encontraron proyectos/i)).toBeInTheDocument();
      });
    });
  });
});
