import styles from './App.module.css'

// Punto de entrada provisional: el routing y los layouts llegan en feature/frontend-base.
function App() {
  return (
    <main className={styles.app}>
      <h1 className={styles.title}>SIGECUE</h1>
      <p className={styles.subtitle}>Sistema de Gestión de Carreras por Encuentro — Universidad de Holguín</p>
    </main>
  )
}

export default App
