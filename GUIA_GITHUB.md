# Guía para subir el proyecto a GitHub

Sigue estos pasos para subir tu proyecto a un nuevo repositorio en GitHub.

## Prerrequisitos
- Tener una cuenta en [GitHub](https://github.com/).
- Tener `git` instalado en tu computadora.

## Pasos

1.  **Crear el repositorio en GitHub**:
    - Ve a https://github.com/new
    - Nombre del repositorio: `backend-transporte-popayan` (o el que prefieras).
    - Descripción: "Backend y Dashboard para App de Transporte en Popayán".
    - **NO** marques "Initialize this repository with a README" (ya lo tenemos localmente).
    - Haz clic en "Create repository".

2.  **Inicializar Git localmente**:
    Abre una terminal en la carpeta de tu proyecto (`c:\Users\estiv\Desktop\Electronic Engineering\SemestreIX\EnfaII\Proyecto_Enfa2\Proyecto_Enfa2`) y ejecuta:

    ```bash
    git init
    ```

3.  **Añadir archivos**:
    Prepara los archivos para ser subidos. El archivo `.gitignore` que hemos creado evitará que se suban archivos innecesarios (como la carpeta `.venv` o archivos temporales).

    ```bash
    git add .
    ```

4.  **Hacer el primer commit**:
    Guarda los cambios en el historial local.

    ```bash
    git commit -m "Initial commit: Backend server and Dashboard"
    ```

5.  **Conectar con GitHub**:
    Copia la URL de tu repositorio (aparecerá después de crearlo en el paso 1, ej. `https://github.com/tu-usuario/backend-transporte-popayan.git`) y ejecuta:

    ```bash
    git branch -M main
    git remote add origin <URL_DE_TU_REPO>
    ```

6.  **Subir los cambios**:
    Envía tu código a GitHub.

    ```bash
    git push -u origin main
    ```

¡Listo! Tu código, junto con las imágenes de arquitectura y la documentación, estará disponible en GitHub.
