import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'

// Con toda la suite en paralelo, la primera carga de una página puede superar
// el 1 s por defecto de findBy*/waitFor: margen para evitar falsos fallos.
configure({ asyncUtilTimeout: 3000 })
