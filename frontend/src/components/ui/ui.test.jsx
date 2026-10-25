import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { vi } from 'vitest'
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Checkbox,
  DataTable,
  Input,
  Modal,
  Pagination,
  Select,
  StatusBadge,
  Stepper,
  ToastProvider,
  useToast,
} from '.'
import { iniciales } from '../../utils/iniciales'

describe('Button', () => {
  it('es type="button" por defecto para no enviar formularios por accidente', () => {
    render(<Button>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' })).toHaveAttribute('type', 'button')
  })

  it('se deshabilita mientras carga', () => {
    render(<Button loading>Guardar</Button>)
    const boton = screen.getByRole('button', { name: 'Guardar' })
    expect(boton).toBeDisabled()
    expect(boton).toHaveAttribute('aria-busy', 'true')
  })

  it('aplica la variante como clase', () => {
    render(<Button variant="danger">Borrar</Button>)
    expect(screen.getByRole('button')).toHaveClass('danger')
  })

  it('puede renderizarse como otro elemento', () => {
    render(
      <Button as="a" href="/login">
        Entrar
      </Button>,
    )
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute('href', '/login')
  })
})

describe('StatusBadge', () => {
  const mapa = { pendiente: { label: 'Pendiente', tone: 'warning' } }

  it('traduce el estado del backend a texto y color', () => {
    render(<StatusBadge estado="pendiente" mapa={mapa} />)
    expect(screen.getByText('Pendiente')).toHaveClass('warning')
  })

  it('muestra el estado tal cual si no está en el mapa', () => {
    render(<StatusBadge estado="otro" mapa={mapa} />)
    expect(screen.getByText('otro')).toHaveClass('neutral')
  })

  it('Badge acepta un tono', () => {
    render(<Badge tone="info">Facultad</Badge>)
    expect(screen.getByText('Facultad')).toHaveClass('info')
  })
})

describe('Campos de formulario', () => {
  it('asocia la etiqueta al control', () => {
    render(<Input label="Carnet de identidad" />)
    expect(screen.getByLabelText('Carnet de identidad')).toBeInTheDocument()
  })

  it('marca el error y lo enlaza con aria-describedby', () => {
    render(<Input label="CI" error="Debe tener 11 dígitos" hint="Sin guiones" />)
    const control = screen.getByLabelText('CI')
    expect(control).toHaveAttribute('aria-invalid', 'true')
    expect(control).toHaveAccessibleDescription('Debe tener 11 dígitos')
    expect(screen.queryByText('Sin guiones')).not.toBeInTheDocument()
  })

  it('muestra la ayuda cuando no hay error', () => {
    render(<Input label="CI" hint="Sin guiones" />)
    expect(screen.getByLabelText('CI')).toHaveAccessibleDescription('Sin guiones')
  })

  it('Select con placeholder y opciones', () => {
    render(<Select label="Entidad" placeholder="Todas" options={[{ value: '1', label: 'Fac. Informática' }]} />)
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual(['Todas', 'Fac. Informática'])
  })

  it('Checkbox con etiqueta y error', () => {
    render(<Checkbox label="Acepto la política" error="Obligatorio" />)
    expect(screen.getByLabelText('Acepto la política')).toHaveAccessibleDescription('Obligatorio')
  })
})

describe('Modal', () => {
  function ModalDePrueba({ onClose = () => {} }) {
    const [abierto, setAbierto] = useState(true)
    return (
      <Modal
        open={abierto}
        onClose={() => {
          onClose()
          setAbierto(false)
        }}
        title="Expresión de interés"
      >
        <input aria-label="Nombre" />
      </Modal>
    )
  }

  it('es un diálogo con título accesible', () => {
    render(<ModalDePrueba />)
    expect(screen.getByRole('dialog', { name: 'Expresión de interés' })).toBeInTheDocument()
  })

  it('se cierra con Escape', () => {
    const onClose = vi.fn()
    render(<ModalDePrueba onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('no renderiza nada cerrado', () => {
    render(<Modal open={false} onClose={() => {}} title="X" />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('DataTable', () => {
  const columnas = [
    { key: 'nombre', header: 'Aspirante' },
    { key: 'indice', header: 'Índice', render: (f) => f.indice.toFixed(1) },
  ]

  it('pinta filas y usa render por columna', () => {
    render(<DataTable columns={columnas} rows={[{ id: 1, nombre: 'María', indice: 92.5 }]} />)
    expect(screen.getByRole('columnheader', { name: 'Aspirante' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '92.5' })).toBeInTheDocument()
  })

  it('muestra el estado vacío', () => {
    render(<DataTable columns={columnas} rows={[]} emptyMessage="Sin solicitudes" />)
    expect(screen.getByText('Sin solicitudes')).toBeInTheDocument()
  })

  it('muestra carga', () => {
    render(<DataTable columns={columnas} rows={[]} loading />)
    expect(screen.getByRole('status')).toHaveTextContent('Cargando datos')
  })
})

describe('Pagination', () => {
  it('calcula el rango y avanza', () => {
    const onChange = vi.fn()
    render(<Pagination page={1} count={45} pageSize={20} onChange={onChange} />)

    expect(screen.getByText('Mostrando 1–20 de 45')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(onChange).toHaveBeenCalledWith(2)
  })

  it('deshabilita siguiente en la última página', () => {
    render(<Pagination page={3} count={45} pageSize={20} onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })
})

describe('Stepper', () => {
  it('marca el paso actual y anuncia el estado de cada paso', () => {
    render(
      <Stepper
        steps={[
          { label: 'Registro', estado: 'completado' },
          { label: 'Perfil', estado: 'actual' },
          { label: 'Carreras', estado: 'pendiente' },
        ]}
      />,
    )
    const actual = screen.getByText('Perfil').closest('li')
    expect(actual).toHaveAttribute('aria-current', 'step')
    expect(screen.getByText('Registro').closest('li')).toHaveTextContent('completado')
  })
})

describe('Avatar', () => {
  it('usa las dos primeras iniciales', () => {
    expect(iniciales('María González Pérez')).toBe('MG')
    render(<Avatar nombre="Juan Castro" />)
    expect(screen.getByText('JC')).toBeInTheDocument()
  })

  it('vuelve a las iniciales si la foto no carga', () => {
    const { container } = render(<Avatar nombre="Juan Castro" foto="/rota.png" />)
    fireEvent.error(container.querySelector('img'))
    expect(screen.getByText('JC')).toBeInTheDocument()
  })
})

describe('Alert y Toast', () => {
  it('los avisos urgentes usan role="alert"', () => {
    render(<Alert tone="danger">Error</Alert>)
    expect(screen.getByRole('alert')).toHaveTextContent('Error')
  })

  it('muestra un toast y permite cerrarlo', () => {
    function Disparador() {
      const toast = useToast()
      return <button onClick={() => toast.exito('Guardado')}>Guardar</button>
    }
    render(
      <ToastProvider>
        <Disparador />
      </ToastProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(screen.getByRole('status')).toHaveTextContent('Guardado')
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar aviso' }))
    expect(screen.queryByText('Guardado')).not.toBeInTheDocument()
  })

  it('useToast fuera del provider falla con un mensaje claro', () => {
    function SinProvider() {
      useToast()
      return null
    }
    vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<SinProvider />)).toThrow('ToastProvider')
  })
})
