import { render, screen } from '@testing-library/react'
import App from './App.jsx'

describe('App', () => {
  it('muestra el nombre del sistema', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'SIGECUE' })).toBeInTheDocument()
  })
})
