# LFL — Logroño Fútbol League

Liga Papeo2 · ESPN League ID **1294118495** · Temporada **2026** · Sport **ffl**.

Fase local de acceso a la liga privada. La web solo lee `data/league.json`. No hay equipos, propietarios, resultados ni plantillas de demostración. El JSON inicial está vacío y muestra **Datos de ESPN no disponibles** hasta una descarga válida.

## Requisitos

Python **3.10 o posterior**. No hay dependencias externas: no necesitas ejecutar pip, Node ni npm.

## Crear .env (PowerShell)

Desde la raíz del proyecto, ejecuta una sola vez:

```powershell
Copy-Item .env.example .env
notepad .env
```

Completa las dos líneas en ese archivo local:

```dotenv
ESPN_S2=PEGA_AQUI_EL_VALOR_DE_LA_COOKIE_espn_s2
ESPN_SWID=PEGA_AQUI_EL_VALOR_DE_LA_COOKIE_SWID
```

Inicia sesión en ESPN con una cuenta que pueda ver la liga. En las herramientas de desarrollador del navegador, abre Almacenamiento / Aplicación → Cookies y busca `espn_s2` y `SWID` para ESPN. Copia únicamente sus valores, sin `Cookie:`, sin punto y coma y sin decodificar. Conserva las llaves de SWID si las incluye el valor original. Guarda y cierra el archivo. No pegues cookies en el código ni las compartas en el chat.

El script lee las credenciales del `.env` de la raíz en local, aunque lo ejecutes desde otra carpeta. En GitHub Actions utiliza exclusivamente las variables de entorno de los Repository Secrets. Acepta valores entre comillas, no requiere dotenv ni realiza interpolaciones. `.env` y sus variantes privadas están ignorados por Git; `.env.example` contiene exclusivamente campos vacíos.

## Actualización automática en GitHub Pages

El workflow `.github/workflows/update-espn.yml` consulta ESPN cada cinco minutos y actualiza únicamente `data/league.json`. Antes de activarlo, crea en el repositorio de GitHub estos **Repository Secrets**:

**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- `ESPN_S2`
- `ESPN_SWID`

No incluyas los valores de estas cookies en el README, el código ni ningún archivo versionado. El workflow los entrega al proceso de Python solo como variables de entorno y no los imprime. La página consulta exclusivamente el JSON publicado, se actualiza de forma silenciosa cada 60 segundos y avisa discretamente si la última descarga supera 15 minutos.

## Descargar los datos

En PowerShell, dentro del proyecto:

```powershell
python scripts/fetch_espn.py
```

Una descarga correcta informa de HTTP 200, el nombre de la liga, el número de equipos y sus nombres, y escribe `data/league.json` de forma atómica. Vuelve a ejecutar el comando para actualizar, y recarga la web.

El script envía las cookies HTTP `espn_s2` y `SWID` al endpoint:

`https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026/segments/0/leagues/1294118495`

Las vistas se envían como parámetros separados: `view=mTeam&view=mRoster&view=mMatchup&view=mMatchupScore&view=mScoreboard&view=mStandings&view=mSettings&view=mStatus`. Nunca se unen con comas. La consulta se inicia directamente en el servidor de lectura, sin redirección desde fantasy.espn.com. Las redirecciones quedan restringidas a HTTPS, puerto 443, ruta `/apis/v3/games/ffl/` y los hosts explícitos `fantasy.espn.com` y `lm-api-reads.fantasy.espn.com`.

- HTTP 401: renueva ambas cookies y comprueba que la cuenta tiene acceso a la liga.
- HTTP 403: acceso denegado por ESPN.
- Error de red, JSON no válido, liga incorrecta o credenciales ausentes: el proceso termina con código 1 y un mensaje controlado, sin imprimir respuestas privadas.
- Ante un error, `data/league.json` se sustituye por un estado vacío no disponible, para no presentar una exportación anterior como actual.

## Ver la web localmente

```powershell
python scripts/serve_local.py
```

Abre **http://127.0.0.1:8000**. Detén el servidor con Ctrl+C. Usa este servidor de archivos permitidos: no sirve `.env`, scripts, README ni el directorio Git. No uses un servidor genérico sobre la raíz que pueda exponer el archivo de credenciales.

Abrir `index.html` con doble clic ya no basta para cargar JSON: los navegadores restringen fetch desde `file://`. En ese caso se muestra el estado no disponible y la indicación de usar el servidor local.

## Datos e interfaz

Se conservan el diseño general, los logos, la intro, las cinco secciones y los detalles. Nombres, propietarios, récords y puntos proceden del JSON de ESPN. Se conserva el cero real; los campos ausentes se muestran como —, nunca como cero inventado. El calendario contiene únicamente los enfrentamientos devueltos por ESPN, con posibles descansos o rivales pendientes.

La clasificación usa la posición recibida de ESPN (`playoffSeed`), sin inventar un orden de clasificación para valores ausentes. El récord de las fichas incluye empates.

Las plantillas de equipo corresponden al scoring period devuelto. Los detalles de enfrentamientos solo muestran la alineación de su periodo cuando la respuesta la contiene. Nunca reutilizan la plantilla actual para un enfrentamiento histórico o futuro. Se conservan por separado los puntos del enfrentamiento y los puntos/proyecciones live, porque pueden cubrir periodos distintos. Los valores semanales de jugadores se filtran por temporada, scoring period y tipo de estadística.

No se inventan probabilidades ni power rankings. Los premios derivados quedan marcados como no disponibles en esta fase de comprobación; la racha se muestra cuando ESPN la devuelve. No se calculan premios sobre históricos o alineaciones incompletos.

El exportador conserva IDs de liga, equipo, partido, jugador, equipo profesional y periodos. Incluye los nombres de propietarios recibidos, pero no correos ni GUID de miembros, que podrían coincidir con la cookie SWID. Solo serializa campos seleccionados, nunca la respuesta cruda ni las cabeceras. También comprueba que los valores de las cookies no aparezcan en el JSON.

## Archivos

- `scripts/fetch_espn.py`: autenticación, consulta, normalización y exportación.
- `scripts/serve_local.py`: servidor limitado a recursos públicos.
- `scripts/test_fetch_espn.py`: pruebas aisladas sin conexión a ESPN.
- `data/league.json`: exportación procesada para la web, inicialmente vacía.
- `.env.example`, `.gitignore`: configuración local sin secretos versionados.
- `js/data.js`: fetch del JSON y validación básica.
- `js/app.js`: navegación, renderizado seguro con textContent y estados vacíos.
- `index.html`, `css/style.css`: interfaz y estilo conservados.
- `manifest.webmanifest`, `service-worker.js`: preparación PWA; `data/league.json` siempre se solicita a red, sin caché antigua.
- `assets/images/`: logos originales.

La sincronización programada usa GitHub Actions y solo realiza commit/push cuando `data/league.json` cambia. La autenticación real solo se puede confirmar al ejecutar el script con cookies válidas de una cuenta autorizada.

## Validación

Ejecuta `python scripts/test_fetch_espn.py` para repetir las diez pruebas del exportador y del servidor. Verifican endpoint directo, parámetros repetidos, nombres de cookies, HTTP 401, redirecciones, campos ausentes frente a cero, periodos de plantillas, lectura exclusiva de .env, exclusión de secretos y rutas públicas. Las diez pruebas pasan. Prueba real autenticada realizada el 10 de septiembre de 2026: HTTP 200, Liga Papeo2, 12 equipos; exportación guardada en `data/league.json`.

Referencia de estructura consultada: [código fuente de espn-api](https://github.com/cwendt94/espn-api/tree/master/espn_api/football). No es una dependencia del proyecto; la API de Fantasy no ofrece un contrato público estable.
