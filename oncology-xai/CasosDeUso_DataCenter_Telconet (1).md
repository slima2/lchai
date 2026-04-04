**TELCONET LATAM**

Área de DataCenter

**Documento de Casos de Uso**

Plataforma Multi-Tenant de Gestión de

Accesos Físicos a Data Centers

Basado en DERCAS v1.0

Formato de Ingeniería de Software

**Marzo 2026**

# 1. Introducción

El presente documento define los Casos de Uso de la Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers de Telconet LATAM. Cada caso de uso ha sido derivado de los Requerimientos Funcionales (RF-01 a RF-08) del documento DERCAS v1.0 y se presenta en formato de ingeniería de software con el nivel de detalle necesario para la fase de diseño e implementación.

Cada caso de uso incluye: objetivo, actores involucrados, precondiciones, disparador, entradas, salidas, flujo básico, flujos alternos, excepciones, reglas de negocio, datos a persistir, integraciones requeridas y ontologías del dominio.

## 1.1 Actores del Sistema

El sistema contempla cuatro actores principales, cada uno con un scope de visibilidad y acción diferenciado:

> • Administrador de Plataforma: Gestión global de tenants, Data Centers, roles y auditoría.
>
> • Administrador de Data Center: Gestión operativa de solicitudes, áreas y agentes de su DC.
>
> • Cliente Telconet (Tenant): Gestión de trabajadores y solicitudes de acceso propias.
>
> • Agente de Seguridad: Escaneo de QR y registro de ingresos en el DC asignado.

# 2. Casos de Uso

## 2.1 CU-01: Gestión de Empresas (Tenants)

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-01: Gestión de Empresas (Tenants)</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir al Administrador de Plataforma crear, editar, activar/desactivar empresas cliente (tenants), asignar acceso a áreas específicas de Data Centers y vincular un usuario tipo Cliente a cada tenant.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Administrador de Plataforma. Actores secundarios: Sistema de autenticación (RBAC), Motor de auditoría.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El Administrador de Plataforma ha iniciado sesión con permisos válidos. Existen Data Centers y áreas registradas en el sistema si se desea asignar acceso.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El Administrador de Plataforma selecciona la opción «Empresas» desde el menú lateral y elige crear, editar o cambiar estado de un tenant.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Nombre de la empresa</p>
<p>• RUC / Identificación fiscal</p>
<p>• Contacto oficial (nombre, email, teléfono)</p>
<p>• Estado inicial (Activo/Inactivo)</p>
<p>• Lista de áreas habilitadas por Data Center</p>
<p>• Datos del usuario tipo Cliente a asignar (nombre, email, rol)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Tenant creado con UUID v7 único y tenant_id propagado</p>
<p>• Usuario tipo Cliente vinculado al tenant</p>
<p>• Confirmación visual del registro exitoso</p>
<p>• Registro de auditoría con acción CREATE_TENANT</p>
<p>• Notificación por email al usuario Cliente creado</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Administrador accede al módulo «Empresas».</p>
<p><strong>2.</strong> Selecciona «Crear Nueva Empresa».</p>
<p><strong>3.</strong> Completa el formulario con datos obligatorios de la empresa.</p>
<p><strong>4.</strong> El sistema valida unicidad de RUC y formato de campos.</p>
<p><strong>5.</strong> El Administrador asigna áreas de Data Centers autorizadas para el tenant.</p>
<p><strong>6.</strong> El sistema verifica que las áreas seleccionadas existan y estén activas.</p>
<p><strong>7.</strong> El Administrador registra los datos del usuario tipo Cliente.</p>
<p><strong>8.</strong> El sistema crea el tenant, asigna UUID v7, propaga tenant_id y crea el usuario con rol Cliente.</p>
<p><strong>9.</strong> El sistema envía notificación por email con credenciales temporales.</p>
<p><strong>10.</strong> El sistema registra el evento en la bitácora de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Editar Empresa — El Administrador selecciona un tenant existente, modifica campos permitidos, el sistema valida y actualiza con registro de auditoría (UPDATE_TENANT).</p>
<p>• FA-02: Desactivar Empresa — El Administrador cambia el estado a Inactivo; el sistema bloquea nuevas solicitudes del tenant pero mantiene datos históricos.</p>
<p>• FA-03: Reactivar Empresa — El Administrador cambia estado a Activo; se rehabilitan permisos de acceso previamente configurados.</p>
<p>• FA-04: Reasignar Áreas — El Administrador modifica las áreas habilitadas; solicitudes pendientes en áreas removidas son notificadas al Admin DC.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: RUC duplicado — El sistema rechaza la creación y muestra mensaje «Ya existe una empresa con este identificador fiscal».</p>
<p>• EX-02: Área inexistente o inactiva — El sistema impide la asignación y alerta que el área no está disponible.</p>
<p>• EX-03: Tenant sin usuario asignado — El sistema bloquea la confirmación y exige la asignación de al menos un usuario tipo Cliente.</p>
<p>• EX-04: Email de usuario duplicado — El sistema rechaza la creación del usuario y solicita un email diferente.</p>
<p>• EX-05: Error de conexión — Se muestra mensaje genérico y se registra el incidente técnico.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: No puede existir un tenant sin al menos un usuario tipo Cliente asignado.</p>
<p>• RN-02: Los datos de cada tenant deben estar aislados por tenant_id (Row Level Security).</p>
<p>• RN-03: No puede asignarse acceso a áreas inexistentes o inactivas.</p>
<p>• RN-04: La desactivación de un tenant no elimina datos históricos, solo bloquea operaciones nuevas.</p>
<p>• RN-05: El RUC debe ser único en toda la plataforma.</p>
<p>• RN-06: Toda acción sobre un tenant genera registro en la bitácora de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Tenant: id (UUID v7), name, ruc, contacto_nombre, contacto_email, contacto_telefono, status, created_at, updated_at</p>
<p>• TenantAreaAccess: id, tenant_id (FK), area_id (FK), granted_at, granted_by</p>
<p>• User: id (UUID v7), tenant_id (FK), email, nombre, rol, status, created_at</p>
<p>• AuditLog: id, actor_id, rol, entidad (Tenant), accion, timestamp, estado_anterior, estado_nuevo, tenant_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Módulo de Autenticación y Autorización (RBAC): Validación de permisos del Administrador.</p>
<p>• Servicio de Email (SMTP/SES): Envío de credenciales al usuario Cliente creado.</p>
<p>• Motor de Auditoría: Registro inmutable de todas las acciones.</p>
<p>• Motor RLS (Row Level Security): Aplicación automática de filtro por tenant_id en cada consulta.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Tenant: Organización cliente que contrata servicios de colocación en Data Centers de Telconet.</p>
<p>• Scope: Ámbito de visibilidad y acción de un rol (global, datacenter, tenant).</p>
<p>• Row Level Security (RLS): Mecanismo de base de datos que restringe filas visibles según el tenant_id del usuario autenticado.</p>
<p>• Área: Subdivisión física dentro de un Data Center (sala, rack, pasillo).</p>
<p>• UUID v7: Identificador único universal con componente temporal para optimizar índices.</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.2 CU-02: Gestión de Data Centers

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-02: Gestión de Data Centers</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir al Administrador de Plataforma crear, editar y administrar Data Centers, incluyendo la gestión de áreas físicas internas, asignación de Administradores DC y creación de cuentas para Agentes de Seguridad.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Administrador de Plataforma. Actores secundarios: Sistema de autenticación (RBAC), Motor de auditoría.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El Administrador de Plataforma ha iniciado sesión con permisos globales. El sistema se encuentra operativo.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El Administrador selecciona «Data Centers» desde el menú y elige crear o administrar un DC.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Nombre del Data Center</p>
<p>• Ubicación (dirección, ciudad, país)</p>
<p>• Estado (Activo/Inactivo)</p>
<p>• Datos de áreas físicas (nombre, descripción, estado)</p>
<p>• Datos del Administrador DC (nombre, email)</p>
<p>• Datos de Agentes de Seguridad (nombre, email)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Data Center registrado con UUID v7</p>
<p>• Áreas creadas y vinculadas al DC</p>
<p>• Administrador DC asignado con scope datacenter_id</p>
<p>• Cuentas de Agentes de Seguridad creadas</p>
<p>• Registro de auditoría con acción CREATE_DATACENTER</p>
<p>• Notificaciones por email a usuarios creados</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Administrador accede al módulo «Data Centers».</p>
<p><strong>2.</strong> Selecciona «Crear Nuevo Data Center».</p>
<p><strong>3.</strong> Completa nombre, ubicación y estado del DC.</p>
<p><strong>4.</strong> El sistema valida unicidad de nombre y formato de datos.</p>
<p><strong>5.</strong> El Administrador crea áreas dentro del DC (nombre, descripción, estado).</p>
<p><strong>6.</strong> El Administrador asigna un Administrador DC (usuario nuevo o existente).</p>
<p><strong>7.</strong> El sistema crea la cuenta con rol Admin DC y scope = datacenter_id.</p>
<p><strong>8.</strong> Opcionalmente, el Administrador crea cuentas de Agentes de Seguridad.</p>
<p><strong>9.</strong> El sistema persiste todos los registros y envía notificaciones.</p>
<p><strong>10.</strong> Se genera registro de auditoría para cada operación.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Editar Data Center — El Administrador actualiza información del DC; el sistema valida y registra cambio.</p>
<p>• FA-02: Desactivar Data Center — El sistema bloquea nuevas solicitudes hacia ese DC y notifica a tenants afectados.</p>
<p>• FA-03: Agregar/Eliminar Áreas — Al eliminar un área, se verifica que no tenga solicitudes pendientes o aprobadas activas.</p>
<p>• FA-04: Reasignar Administrador DC — Se revoca scope al anterior y se asigna al nuevo; se notifica a ambos.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Nombre de DC duplicado — El sistema rechaza y solicita nombre único.</p>
<p>• EX-02: Área con solicitudes activas al intentar eliminar — El sistema bloquea la eliminación y sugiere desactivar.</p>
<p>• EX-03: Email duplicado al crear Administrador DC o Agente — El sistema solicita email diferente.</p>
<p>• EX-04: Intento de crear DC sin al menos un área — El sistema permite creación, pero alerta que no será operativo sin áreas.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: Cada área pertenece a un único Data Center.</p>
<p>• RN-02: Un Administrador DC solo puede visualizar y gestionar información de su propio DC.</p>
<p>• RN-03: Un Agente de Seguridad solo puede escanear QR del DC asignado.</p>
<p>• RN-04: La desactivación de un DC no elimina registros históricos.</p>
<p>• RN-05: Toda acción sobre DC genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• DataCenter: id (UUID v7), name, location, ciudad, pais, status, created_at, updated_at</p>
<p>• Area: id (UUID), datacenter_id (FK), name, descripcion, status, created_at</p>
<p>• User (Admin DC): id, email, nombre, rol=ADMIN_DC, scope=datacenter_id</p>
<p>• User (Agente): id, email, nombre, rol=AGENTE_SEGURIDAD, scope=datacenter_id</p>
<p>• AuditLog: id, actor_id, rol, entidad, accion, timestamp, estado_anterior, estado_nuevo, datacenter_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Módulo RBAC: Asignación de roles con scope por datacenter_id.</p>
<p>• Servicio de Email: Notificaciones a Admins DC y Agentes creados.</p>
<p>• Motor de Auditoría: Registro inmutable de cada operación.</p>
<p>• Motor RLS: Filtro automático por datacenter_id en consultas de Admin DC y Agentes.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Data Center: Instalación física administrada por Telconet donde se alojan equipos de los tenants.</p>
<p>• Área: Zona física delimitada dentro del DC (sala de servidores, rack, zona de energía, pasillo frío/caliente).</p>
<p>• Administrador DC: Rol con scope limitado a un DC específico para gestionar solicitudes y operaciones.</p>
<p>• Agente de Seguridad: Rol operativo con acceso únicamente a funciones de escaneo y registro en su DC.</p>
<p>• Scope: Delimitador de visibilidad que restringe la acción del rol a un contexto específico (global, datacenter, tenant).</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.3 CU-03: Gestión de Trabajadores

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-03: Gestión de Trabajadores</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir a cada empresa cliente (tenant) registrar, editar, activar y desactivar a sus trabajadores que podrán ser incluidos en solicitudes de acceso físico a Data Centers.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Cliente Telconet (Tenant). Actores secundarios: Motor de auditoría, Motor RLS.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El usuario Cliente ha iniciado sesión con permisos válidos. El tenant se encuentra en estado Activo.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El usuario Cliente selecciona «Trabajadores» desde el menú y elige crear o gestionar un trabajador.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Nombres del trabajador</p>
<p>• Apellidos del trabajador</p>
<p>• Cédula de identidad</p>
<p>• Email del trabajador</p>
<p>• Teléfono de contacto</p>
<p>• Estado (Activo/Inactivo)</p>
<p>• Documentos adjuntos (certificaciones, opcional)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Trabajador registrado con UUID y vinculado al tenant_id</p>
<p>• Confirmación visual del registro exitoso</p>
<p>• Registro de auditoría con acción CREATE_WORKER</p>
<p>• Trabajador disponible para solicitudes de acceso</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Cliente accede al módulo «Trabajadores».</p>
<p><strong>2.</strong> Selecciona «Crear Nuevo Trabajador».</p>
<p><strong>3.</strong> Completa nombres, apellidos, cédula, email y teléfono.</p>
<p><strong>4.</strong> El sistema valida formato de cédula ecuatoriana y unicidad dentro del tenant.</p>
<p><strong>5.</strong> Opcionalmente, el Cliente adjunta certificaciones o documentos.</p>
<p><strong>6.</strong> El sistema persiste el trabajador con tenant_id del usuario autenticado.</p>
<p><strong>7.</strong> Se muestra confirmación y se genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Editar Trabajador — El Cliente modifica datos permitidos; la cédula no puede cambiarse tras creación.</p>
<p>• FA-02: Desactivar Trabajador — El sistema bloquea inclusión en nuevas solicitudes; solicitudes existentes no se afectan.</p>
<p>• FA-03: Reactivar Trabajador — El trabajador vuelve a estar disponible para solicitudes.</p>
<p>• FA-04: Adjuntar Documentos — El Cliente añade certificaciones posteriores al registro.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Cédula duplicada dentro del tenant — El sistema rechaza con mensaje «Ya existe un trabajador con esta cédula en su empresa».</p>
<p>• EX-02: Formato de cédula inválido — El sistema muestra error de validación y detalla el formato esperado.</p>
<p>• EX-03: Tenant inactivo — El sistema bloquea toda operación y redirige a pantalla informativa.</p>
<p>• EX-04: Archivo adjunto excede tamaño máximo — El sistema rechaza con mensaje de límite.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: Los trabajadores no poseen cuenta de usuario en el sistema; son registros de datos.</p>
<p>• RN-02: La visibilidad de trabajadores es exclusiva del tenant propietario (RLS por tenant_id).</p>
<p>• RN-03: La cédula debe ser única dentro de cada tenant.</p>
<p>• RN-04: No puede crearse una solicitud de acceso con un trabajador en estado Inactivo.</p>
<p>• RN-05: Debe validarse el formato de identificación (cédula ecuatoriana: 10 dígitos con validación de dígito verificador).</p>
<p>• RN-06: La eliminación física no está permitida; solo desactivación lógica.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Worker: id (UUID), tenant_id (FK), nombres, apellidos, cedula, email, telefono, status, created_at, updated_at</p>
<p>• WorkerDocument: id, worker_id (FK), tipo_documento, nombre_archivo, ruta_almacenamiento, uploaded_at</p>
<p>• AuditLog: id, actor_id, rol, entidad (Worker), accion, timestamp, estado_anterior, estado_nuevo, tenant_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Motor RLS: Filtro automático por tenant_id para garantizar aislamiento.</p>
<p>• Motor de Auditoría: Registro de cada operación CRUD sobre trabajadores.</p>
<p>• Servicio de Almacenamiento (S3 / Object Storage): Almacenamiento de documentos adjuntos.</p>
<p>• Validador de Cédula Ecuatoriana: Verificación de dígito verificador según algoritmo oficial.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Trabajador (Worker): Persona física empleada por un tenant que puede acceder a un Data Center.</p>
<p>• Cédula: Documento de identidad ecuatoriano (10 dígitos) utilizado como identificador único por tenant.</p>
<p>• Certificación: Documento que acredita competencia técnica del trabajador (ej. certificación eléctrica, seguridad).</p>
<p>• Tenant: Contexto organizacional al que pertenece el trabajador; delimita la visibilidad de sus datos.</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.4 CU-04: Solicitud de Acceso Físico

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-04: Solicitud de Acceso Físico</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir al usuario Cliente crear solicitudes de ingreso físico a un Data Center para uno de sus trabajadores, especificando áreas, horario, trabajo a realizar y documentación de soporte.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Cliente Telconet (Tenant). Actores secundarios: Motor de validación, Motor de auditoría, Servicio de notificaciones.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El tenant está activo. Existen trabajadores activos registrados. El tenant tiene áreas habilitadas en al menos un DC.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El usuario Cliente selecciona «Solicitudes» → «Crear Nueva Solicitud».</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Data Center destino (selector filtrado por áreas habilitadas)</p>
<p>• Trabajador (selector filtrado por trabajadores activos del tenant)</p>
<p>• Descripción del trabajo a realizar</p>
<p>• Lista de herramientas a ingresar</p>
<p>• Número de contacto en sitio</p>
<p>• Email de contacto</p>
<p>• Áreas solicitadas (selección múltiple de áreas autorizadas)</p>
<p>• Horario inicio (fecha y hora)</p>
<p>• Horario fin (fecha y hora)</p>
<p>• Documentos adjuntos (orden de trabajo, certificaciones)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Solicitud creada en estado PENDIENTE con UUID</p>
<p>• Notificación al Administrador DC del Data Center destino</p>
<p>• Confirmación visual al Cliente con número de solicitud</p>
<p>• Registro de auditoría con acción CREATE_ACCESS_REQUEST</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Cliente accede a «Solicitudes» y selecciona «Crear Nueva Solicitud».</p>
<p><strong>2.</strong> Selecciona el Data Center destino (filtrado por DC con áreas habilitadas para su tenant).</p>
<p><strong>3.</strong> Selecciona el trabajador (filtrado por trabajadores activos).</p>
<p><strong>4.</strong> Completa descripción del trabajo, herramientas, contacto y email.</p>
<p><strong>5.</strong> Selecciona una o más áreas autorizadas dentro del DC seleccionado.</p>
<p><strong>6.</strong> Define horario de inicio y fin (ambos deben ser futuros).</p>
<p><strong>7.</strong> Adjunta documentos de soporte (orden de trabajo, certificaciones).</p>
<p><strong>8.</strong> El sistema valida reglas de negocio: horario futuro, áreas autorizadas, trabajador activo.</p>
<p><strong>9.</strong> El sistema crea la solicitud en estado PENDIENTE y asigna UUID.</p>
<p><strong>10.</strong> Se envía notificación al Administrador DC para revisión.</p>
<p><strong>11.</strong> Se genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Consultar Solicitudes — El Cliente navega por subsecciones (Pendientes, Aprobadas, Denegadas, Historial).</p>
<p>• FA-02: Descargar QR — Disponible solo para solicitudes en estado APROBADA; el Cliente descarga el QR generado.</p>
<p>• FA-03: Ver Motivo de Denegación — Para solicitudes DENEGADAS, el Cliente visualiza el motivo registrado por el Admin DC.</p>
<p>• FA-04: Cancelar Solicitud — El Cliente cancela una solicitud en estado PENDIENTE antes de la revisión.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Horario no futuro — El sistema rechaza e indica que ambas fechas deben ser posteriores al momento actual.</p>
<p>• EX-02: Área no autorizada — El sistema no muestra áreas no habilitadas para el tenant; si se fuerza por API, rechaza con error 403.</p>
<p>• EX-03: Trabajador inactivo — El sistema bloquea la creación y solicita seleccionar un trabajador activo.</p>
<p>• EX-04: Horario fin anterior a horario inicio — El sistema rechaza con mensaje de validación.</p>
<p>• EX-05: Data Center inactivo — No aparece en el selector; si se fuerza por API, retorna error.</p>
<p>• EX-06: Tenant inactivo — Se bloquea toda operación con redirección informativa.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: Solo pueden seleccionarse áreas autorizadas para el tenant en el DC seleccionado.</p>
<p>• RN-02: El horario de inicio y fin deben ser estrictamente futuros al momento de creación.</p>
<p>• RN-03: No puede crearse solicitud con un trabajador inactivo.</p>
<p>• RN-04: Una solicitud no puede modificarse una vez aprobada.</p>
<p>• RN-05: La solicitud se crea siempre en estado PENDIENTE.</p>
<p>• RN-06: Estados válidos de una solicitud: Pendiente, Aprobada, Denegada, Expirada, Utilizada.</p>
<p>• RN-07: Las solicitudes expiradas son aquellas cuyo horario_fin se cumplió sin ser utilizadas.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• AccessRequest: id (UUID), tenant_id (FK), datacenter_id (FK), worker_id (FK), trabajo, herramientas, contacto_telefono, contacto_email, horario_inicio, horario_fin, status (PENDIENTE), created_at, created_by</p>
<p>• AccessRequestArea: id, request_id (FK), area_id (FK)</p>
<p>• AccessRequestDocument: id, request_id (FK), nombre_archivo, ruta, tipo, uploaded_at</p>
<p>• AuditLog: id, actor_id, rol, entidad (AccessRequest), accion (CREATE), timestamp, tenant_id, datacenter_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Motor RLS: Filtro por tenant_id en todas las consultas del Cliente.</p>
<p>• Servicio de Notificaciones (Email/Push): Alerta al Administrador DC.</p>
<p>• Servicio de Almacenamiento: Documentos adjuntos (S3/Object Storage).</p>
<p>• Motor de Auditoría: Registro de creación con detalle completo.</p>
<p>• Scheduler/Cron: Proceso de expiración automática de solicitudes cuyo horario_fin ha pasado.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Solicitud de Acceso (AccessRequest): Petición formal de un tenant para que un trabajador ingrese a áreas de un DC.</p>
<p>• Horario de Acceso: Ventana temporal (inicio–fin) dentro de la cual se autoriza el ingreso físico.</p>
<p>• Estado de Solicitud: Ciclo de vida (Pendiente → Aprobada/Denegada → Utilizada/Expirada).</p>
<p>• Área Autorizada: Área del DC a la que el tenant tiene permiso de solicitar acceso.</p>
<p>• Documento de Soporte: Archivo adjunto que respalda la solicitud (orden de trabajo, certificaciones).</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.5 CU-05: Aprobación / Denegación de Solicitud

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-05: Aprobación / Denegación de Solicitud</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir al Administrador de Data Center revisar solicitudes de acceso pendientes y decidir aprobar o denegar cada solicitud, registrando obligatoriamente el motivo en caso de denegación.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Administrador de Data Center. Actores secundarios: Motor de auditoría, Servicio de notificaciones, Generador de QR.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El Administrador DC ha iniciado sesión con permisos válidos para su DC. Existen solicitudes en estado PENDIENTE para su DC.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El Administrador DC accede a «Solicitudes» → «Pendientes» y selecciona una solicitud para revisar.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• ID de la solicitud a revisar</p>
<p>• Decisión: Aprobar o Denegar</p>
<p>• Comentario del aprobador (obligatorio siempre)</p>
<p>• Motivo de denegación (obligatorio si deniega)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Solicitud actualizada a estado APROBADA o DENEGADA</p>
<p>• Registro de aprobador (usuario, fecha/hora, comentario)</p>
<p>• QR generado (solo si se aprueba) — dispara CU-06</p>
<p>• Notificación al Cliente sobre la decisión</p>
<p>• Registro de auditoría con acción APPROVE_REQUEST o DENY_REQUEST</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Administrador DC accede a «Solicitudes Pendientes».</p>
<p><strong>2.</strong> Selecciona una solicitud y revisa: trabajador, áreas, horario, documentos adjuntos.</p>
<p><strong>3.</strong> El Administrador decide aprobar la solicitud.</p>
<p><strong>4.</strong> Ingresa un comentario obligatorio.</p>
<p><strong>5.</strong> El sistema registra: aprobado_por, aprobado_en, comentario.</p>
<p><strong>6.</strong> El sistema cambia estado a APROBADA.</p>
<p><strong>7.</strong> Se dispara la generación del QR firmado criptográficamente (CU-06).</p>
<p><strong>8.</strong> Se notifica al Cliente por email con confirmación y acceso al QR.</p>
<p><strong>9.</strong> Se genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Denegar Solicitud — El Admin DC selecciona «Denegar», ingresa motivo obligatorio, el sistema cambia a DENEGADA y notifica al Cliente con el motivo.</p>
<p>• FA-02: Solicitar Información Adicional — El Admin DC puede agregar observación y mantener en PENDIENTE (no cambia estado).</p>
<p>• FA-03: Revisión de Adjuntos — El Admin DC descarga y revisa documentos adjuntos antes de decidir.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Solicitud ya procesada — Si otro Admin ya aprobó/denegó, el sistema muestra alerta de concurrencia.</p>
<p>• EX-02: Denegación sin motivo — El sistema bloquea la acción hasta que se ingrese un motivo.</p>
<p>• EX-03: Solicitud expirada — Si el horario_fin ya pasó, el sistema impide aprobación y marca como EXPIRADA.</p>
<p>• EX-04: Error en generación de QR — La solicitud se marca como APROBADA pero se registra error técnico para reintento.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: Solo el Administrador DC del DC destino puede aprobar/denegar solicitudes de su DC.</p>
<p>• RN-02: La denegación requiere motivo obligatorio.</p>
<p>• RN-03: El comentario del aprobador es obligatorio tanto para aprobación como denegación.</p>
<p>• RN-04: Se debe registrar: usuario aprobador, fecha y hora, comentario.</p>
<p>• RN-05: La aprobación dispara automáticamente la generación del QR.</p>
<p>• RN-06: No puede aprobarse una solicitud cuyo horario ya expiró.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• AccessRequest (UPDATE): status (APROBADA/DENEGADA), aprobado_por (FK a User), aprobado_en (timestamp), comentario_aprobador, motivo_denegacion</p>
<p>• AuditLog: id, actor_id (Admin DC), rol, entidad (AccessRequest), accion (APPROVE/DENY), timestamp, estado_anterior (PENDIENTE), estado_nuevo, datacenter_id, tenant_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Motor RBAC: Validación de que el Admin DC tiene scope sobre el DC de la solicitud.</p>
<p>• Servicio de Notificaciones: Email al Cliente informando decisión.</p>
<p>• Generador de QR (CU-06): Invocado automáticamente tras aprobación.</p>
<p>• Motor de Auditoría: Registro con before/after state de la solicitud.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Aprobación: Acto formal del Admin DC que autoriza el ingreso físico y dispara la generación de credenciales QR.</p>
<p>• Denegación: Rechazo fundamentado de una solicitud de acceso con motivo registrado.</p>
<p>• Aprobador: Usuario con rol Admin DC que tiene potestad de decidir sobre solicitudes de su DC.</p>
<p>• Motivo de Denegación: Texto obligatorio que justifica el rechazo de la solicitud.</p>
<p>• Concurrencia: Situación donde múltiples administradores intentan procesar la misma solicitud simultáneamente.</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.6 CU-06: Generación de Código QR Firmado

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-06: Generación de Código QR Firmado</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Generar un código QR estático con token firmado criptográficamente que contenga los datos de la solicitud aprobada, con expiración temporal y validez para un único ingreso.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Sistema (proceso automático). Actores secundarios: Servicio criptográfico, Motor de auditoría.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>La solicitud ha sido aprobada (estado APROBADA). La clave privada de firma está disponible en el sistema.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>Evento de aprobación de solicitud (CU-05 finalizado exitosamente).</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• ID de la solicitud aprobada</p>
<p>• Datos de la solicitud: trabajador, DC, áreas, horario_inicio, horario_fin</p>
<p>• Clave privada del sistema para firma digital</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Token firmado criptográficamente (JWT o similar con RS256)</p>
<p>• Código QR generado como imagen (PNG/SVG)</p>
<p>• Hash del token almacenado en base de datos</p>
<p>• Registro de auditoría con acción GENERATE_QR</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El sistema recibe el evento de aprobación con el ID de la solicitud.</p>
<p><strong>2.</strong> Recupera los datos completos de la solicitud (trabajador, DC, áreas, horario).</p>
<p><strong>3.</strong> Construye el payload del token: request_id, worker_id, datacenter_id, areas, horario_inicio, horario_fin, expira_en.</p>
<p><strong>4.</strong> Firma el payload con la clave privada del sistema (algoritmo RS256).</p>
<p><strong>5.</strong> Genera el hash del token y lo almacena en la entidad QRToken.</p>
<p><strong>6.</strong> Codifica el token en formato QR estático (imagen PNG).</p>
<p><strong>7.</strong> Asocia el QR a la solicitud y lo marca como no utilizado.</p>
<p><strong>8.</strong> Se genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Regenerar QR — El Admin DC solicita regeneración; se invalida el token anterior y se crea uno nuevo.</p>
<p>• FA-02: QR para visualización — El Admin DC puede visualizar el QR desde la pantalla de solicitudes aprobadas.</p>
<p>• FA-03: Descarga por Cliente — El Cliente descarga el QR como imagen o PDF desde su portal.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Error en servicio criptográfico — El sistema reintenta 3 veces; si falla, marca la solicitud con flag de error_qr y alerta al Admin.</p>
<p>• EX-02: Solicitud ya tiene QR válido — Se rechaza la generación duplicada.</p>
<p>• EX-03: Horario ya expirado al generar — El sistema no genera QR y cambia la solicitud a EXPIRADA.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: El QR es estático: contiene toda la información necesaria para validación.</p>
<p>• RN-02: El token debe estar firmado criptográficamente (RS256 o equivalente).</p>
<p>• RN-03: El token incluye expiración que coincide con horario_fin de la solicitud.</p>
<p>• RN-04: El QR es válido solo dentro del horario aprobado (horario_inicio – horario_fin).</p>
<p>• RN-05: El QR es válido para un único ingreso (una vez escaneado exitosamente, se marca como utilizado).</p>
<p>• RN-06: El hash del token se almacena; no se guarda el token en texto plano.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• QRToken: id (UUID), request_id (FK), token_hash, expira_en (timestamp), usado (boolean, default false), usado_en (timestamp nullable), created_at</p>
<p>• AuditLog: id, actor_id (SYSTEM), entidad (QRToken), accion (GENERATE_QR), timestamp, request_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Servicio Criptográfico: Firma RS256 con clave privada del sistema.</p>
<p>• Generador de QR: Librería de generación de códigos QR (qrcode, ZXing, etc.).</p>
<p>• Motor de Auditoría: Registro de generación de token.</p>
<p>• Servicio de Almacenamiento: Imagen QR almacenada para descarga.</p>
<p>• Servicio de Notificaciones: Alerta al Cliente de que su QR está disponible.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Token QR: Cadena de datos firmada digitalmente que codifica la autorización de ingreso físico.</p>
<p>• Firma Criptográfica (RS256): Algoritmo asimétrico que garantiza la integridad y autenticidad del token.</p>
<p>• Expiración: Momento temporal tras el cual el token pierde validez automáticamente.</p>
<p>• Token Hash: Huella digital del token almacenada en BD para verificación sin exponer el token original.</p>
<p>• QR Estático: Código QR cuyo contenido no cambia y puede leerse sin conexión al servidor.</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.7 CU-07: Escaneo y Validación de QR por Agente

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-07: Escaneo y Validación de QR por Agente de Seguridad</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir al Agente de Seguridad escanear el código QR presentado por un trabajador, validar automáticamente las condiciones de acceso y registrar el ingreso o rechazo con observaciones y evidencia.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Agente de Seguridad. Actores secundarios: Motor de validación criptográfica, Motor de auditoría.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El Agente de Seguridad ha iniciado sesión con rol y scope del DC asignado. El dispositivo tiene cámara activa o campo de ingreso manual.</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>Un trabajador se presenta en la entrada del Data Center y muestra su código QR al Agente.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Código QR escaneado (vía cámara o ingreso manual del código)</p>
<p>• Observaciones del Agente (texto libre, opcional)</p>
<p>• Imágenes adjuntas (evidencia fotográfica, opcional)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Resultado de validación: VÁLIDO, EXPIRADO, YA_UTILIZADO, FUERA_DE_HORARIO, FIRMA_INVÁLIDA, DC_INCORRECTO</p>
<p>• Si válido: Registro de ingreso (AccessScanEvent) y token marcado como utilizado</p>
<p>• Si inválido: Registro de intento fallido con motivo</p>
<p>• Resultado inmediato visual para el Agente (pantalla verde/roja)</p>
<p>• Registro de auditoría con acción SCAN_QR</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El Agente abre la función «Escanear QR».</p>
<p><strong>2.</strong> Escanea el QR con la cámara del dispositivo.</p>
<p><strong>3.</strong> El sistema extrae el token del QR.</p>
<p><strong>4.</strong> El sistema verifica la firma criptográfica con la clave pública.</p>
<p><strong>5.</strong> Verifica que el token no haya expirado (expira_en &gt; ahora).</p>
<p><strong>6.</strong> Verifica que el token no haya sido utilizado previamente (usado = false).</p>
<p><strong>7.</strong> Verifica que el horario actual esté dentro del rango aprobado (horario_inicio ≤ ahora ≤ horario_fin).</p>
<p><strong>8.</strong> Verifica que el DC del token coincida con el DC del Agente.</p>
<p><strong>9.</strong> Si todas las validaciones pasan: muestra resultado VÁLIDO (pantalla verde).</p>
<p><strong>10.</strong> El sistema registra el ingreso (AccessScanEvent) y marca el token como usado.</p>
<p><strong>11.</strong> El Agente opcionalmente agrega observaciones e imágenes.</p>
<p><strong>12.</strong> Se genera registro de auditoría.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Ingreso Manual de Código — Si la cámara falla, el Agente ingresa el código manualmente; el flujo de validación es idéntico.</p>
<p>• FA-02: Registrar Incidente — Tras un rechazo, el Agente registra un incidente con descripción y evidencia fotográfica.</p>
<p>• FA-03: Consultar Ingresos del Día — El Agente accede al listado de ingresos registrados con filtros.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Firma inválida — Pantalla roja con mensaje «QR inválido: firma no verificada». Se registra intento.</p>
<p>• EX-02: Token expirado — Pantalla roja con «Acceso expirado». Se registra intento.</p>
<p>• EX-03: Token ya utilizado — Pantalla roja con «QR ya utilizado» y se muestra fecha/hora del uso anterior.</p>
<p>• EX-04: Fuera de horario — Pantalla roja con «Fuera del horario autorizado (HH:MM – HH:MM)».</p>
<p>• EX-05: DC incorrecto — Pantalla roja con «Este QR no corresponde a este Data Center».</p>
<p>• EX-06: Error de lectura de QR — Se solicita reintento o ingreso manual.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: Si cualquier validación falla, se rechaza el acceso y se registra el intento.</p>
<p>• RN-02: El token se marca como utilizado inmediatamente tras un ingreso válido (usado = true, usado_en = now).</p>
<p>• RN-03: El Agente solo puede escanear QR pertenecientes a su DC asignado.</p>
<p>• RN-04: La validación de firma se realiza con clave pública (verificación offline posible).</p>
<p>• RN-05: Tanto ingresos exitosos como rechazados generan registro en AccessScanEvent.</p>
<p>• RN-06: La solicitud asociada cambia a estado UTILIZADA tras ingreso válido.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• AccessScanEvent: id (UUID), request_id (FK), agente_id (FK), fecha (timestamp), resultado (VALIDO/EXPIRADO/USADO/FUERA_HORARIO/FIRMA_INVALIDA/DC_INCORRECTO), observaciones, datacenter_id</p>
<p>• ScanEvidence: id, scan_event_id (FK), imagen_ruta, uploaded_at</p>
<p>• QRToken (UPDATE): usado = true, usado_en = timestamp (solo si validación exitosa)</p>
<p>• AccessRequest (UPDATE): status = UTILIZADA (solo si validación exitosa)</p>
<p>• AuditLog: id, actor_id (Agente), entidad (AccessScanEvent), accion (SCAN_QR), resultado, timestamp, datacenter_id</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Motor Criptográfico: Verificación de firma RS256 con clave pública.</p>
<p>• Cámara del Dispositivo: API de escaneo QR (nativo o web).</p>
<p>• Motor de Auditoría: Registro de cada escaneo (exitoso o fallido).</p>
<p>• Servicio de Almacenamiento: Imágenes de evidencia (S3/Object Storage).</p>
<p>• Motor RLS: Verificación de que el Agente opera en su DC asignado.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Escaneo (ScanEvent): Acción de lectura y validación de un QR por parte de un Agente en un DC.</p>
<p>• Validación Criptográfica: Proceso de verificar la autenticidad e integridad del token usando clave pública.</p>
<p>• Resultado de Escaneo: Estado resultante de la validación (Válido, Expirado, Usado, Fuera de Horario, Firma Inválida, DC Incorrecto).</p>
<p>• Evidencia: Material fotográfico o textual que complementa el registro del escaneo.</p>
<p>• Token Utilizado: Estado irreversible del QR tras un ingreso exitoso, que impide su reutilización.</p>
</blockquote></td>
</tr>
</tbody>
</table>

## 2.8 CU-08: Registro y Reporte de Visitas

<table>
<colgroup>
<col style="width: 25%" />
<col style="width: 74%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2"><strong>CU-08: Registro y Reporte de Visitas</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Objetivo</strong></td>
<td>Permitir consultar, filtrar y exportar reportes de visitas físicas registradas a los Data Centers, segmentados por período, empresa, área y Data Center, según el rol del usuario.</td>
</tr>
<tr class="even">
<td><strong>Actores</strong></td>
<td>Actor principal: Administrador de Plataforma, Administrador DC, Cliente Telconet. Actor secundario: Motor de auditoría.</td>
</tr>
<tr class="odd">
<td><strong>Precondiciones</strong></td>
<td>El usuario ha iniciado sesión con permisos válidos. Existen registros de visitas (AccessScanEvent con resultado VÁLIDO).</td>
</tr>
<tr class="even">
<td><strong>Disparador</strong></td>
<td>El usuario accede a «Registro de Visitas» o «Reportes» desde el menú lateral.</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Entradas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Filtro de período: Diario, Semanal, Mensual o rango personalizado</p>
<p>• Filtro por empresa (tenant) — disponible para Admin Plataforma y Admin DC</p>
<p>• Filtro por Data Center — disponible para Admin Plataforma</p>
<p>• Filtro por área — disponible para Admin Plataforma y Admin DC</p>
<p>• Filtro por trabajador — disponible para Cliente</p>
<p>• Formato de exportación (CSV, PDF, Excel)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Salidas</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Listado de visitas con: fecha, trabajador, empresa, DC, áreas, agente, resultado</p>
<p>• Indicadores agregados: total visitas, visitas por empresa, por DC, por área</p>
<p>• Archivo exportado en formato seleccionado</p>
<p>• Gráficos de tendencia (dashboard)</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujo Básico</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p><strong>1.</strong> El usuario accede a «Registro de Visitas» / «Reportes».</p>
<p><strong>2.</strong> El sistema muestra el listado por defecto según scope: global (Admin Plataforma), DC (Admin DC), propias (Cliente).</p>
<p><strong>3.</strong> El usuario aplica filtros: período, empresa, DC, área, trabajador.</p>
<p><strong>4.</strong> El sistema ejecuta la consulta con filtros RLS automáticos según el rol.</p>
<p><strong>5.</strong> Se muestra el listado de visitas con datos detallados.</p>
<p><strong>6.</strong> El usuario visualiza indicadores agregados y gráficos de tendencia.</p>
<p><strong>7.</strong> Opcionalmente, el usuario selecciona formato de exportación y descarga el reporte.</p>
<p><strong>8.</strong> Se genera registro de auditoría para la acción de consulta/exportación.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Flujos Alternos</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• FA-01: Dashboard Global (Admin Plataforma) — Visualización consolidada con solicitudes por estado, por DC y por tenant.</p>
<p>• FA-02: Dashboard Operativo (Admin DC) — Solicitudes pendientes, aprobadas hoy, próximos ingresos.</p>
<p>• FA-03: Dashboard Cliente — Resumen de solicitudes propias, próximos accesos, historial.</p>
<p>• FA-04: Reporte por Agente — El Admin DC consulta actividad de escaneos por agente específico.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Excepciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• EX-01: Sin resultados — El sistema muestra mensaje informativo «No se encontraron visitas con los filtros aplicados».</p>
<p>• EX-02: Exportación con demasiados registros — El sistema limita a 10,000 registros o genera exportación asíncrona.</p>
<p>• EX-03: Error de generación de reporte — Se notifica al usuario y se registra el error técnico.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Reglas de Negocio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• RN-01: El Admin Plataforma ve reportes globales (todos los DC, todos los tenants).</p>
<p>• RN-02: El Admin DC ve solo visitas de su Data Center.</p>
<p>• RN-03: El Cliente ve solo visitas de sus propios trabajadores.</p>
<p>• RN-04: El Agente ve un resumen parcial: ingresos del día y su propia actividad.</p>
<p>• RN-05: Toda consulta de reportes aplica RLS automático según scope del usuario.</p>
<p>• RN-06: Las exportaciones deben incluir marca de agua con fecha de generación y usuario que exportó.</p>
<p>• RN-07: Los reportes incluyen tanto ingresos exitosos como intentos rechazados.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Datos a Persistir</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• ReportExportLog: id, user_id, tipo_reporte, filtros_aplicados (JSON), formato, registros_exportados, timestamp</p>
<p>• AuditLog: id, actor_id, rol, entidad (Report), accion (VIEW_REPORT/EXPORT_REPORT), timestamp, filtros</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Integraciones</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Motor RLS: Filtro automático por scope (global, datacenter_id, tenant_id).</p>
<p>• Motor de Auditoría: Registro de cada consulta y exportación.</p>
<p>• Generador de Reportes: Exportación a CSV, PDF y Excel.</p>
<p>• Motor de Visualización (Dashboard): Gráficos de tendencia, indicadores KPI.</p>
<p>• Motor de Consultas Indexadas: Índices por tenant_id, datacenter_id, fecha para rendimiento.</p>
</blockquote></td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Ontologías / Conceptos del Dominio</strong></td>
</tr>
<tr class="even">
<td colspan="2"><blockquote>
<p>• Visita: Evento de ingreso físico exitosamente validado y registrado en un Data Center.</p>
<p>• Reporte: Consolidación de datos de visitas filtrados por criterios específicos, presentados en formato tabular o gráfico.</p>
<p>• Scope de Visibilidad: Nivel de acceso a datos de reportes según el rol (Global &gt; DC &gt; Tenant &gt; Agente).</p>
<p>• Indicador KPI: Métrica agregada que resume la actividad de visitas (total, por período, por empresa).</p>
<p>• Exportación: Proceso de generar un archivo descargable con los datos del reporte en formato estructurado.</p>
</blockquote></td>
</tr>
</tbody>
</table>

# 3. Matriz de Trazabilidad

La siguiente tabla establece la correspondencia entre los Requerimientos Funcionales del DERCAS y los Casos de Uso definidos en este documento:

| **Req. ID** | **Requerimiento Funcional**   | **Caso de Uso** |
|-------------|-------------------------------|-----------------|
| RF-01       | Gestión de Empresas (Tenants) | **CU-01**       |
| RF-02       | Gestión de Data Centers       | **CU-02**       |
| RF-03       | Gestión de Trabajadores       | **CU-03**       |
| RF-04       | Solicitud de Acceso           | **CU-04**       |
| RF-05       | Aprobación                    | **CU-05**       |
| RF-06       | Generación de QR              | **CU-06**       |
| RF-07       | Escaneo por Agente            | **CU-07**       |
| RF-08       | Registro de Visitas           | **CU-08**       |

# 4. Glosario de Términos

| **Término**     | **Definición**                                                                           |
|-----------------|------------------------------------------------------------------------------------------|
| **Tenant**      | Organización cliente que contrata servicios de colocación en Data Centers de Telconet.   |
| **RBAC**        | Role-Based Access Control. Modelo de control de acceso basado en roles desacoplados.     |
| **RLS**         | Row Level Security. Mecanismo de aislamiento de datos a nivel de fila en base de datos.  |
| **Scope**       | Ámbito de visibilidad y acción de un rol: global, datacenter o tenant.                   |
| **UUID v7**     | Identificador universal único con componente temporal para optimización de índices.      |
| **RS256**       | Algoritmo de firma criptográfica asimétrica (RSA con SHA-256).                           |
| **QR Estático** | Código QR cuyo contenido es fijo y puede validarse sin conexión al servidor.             |
| **Token Hash**  | Huella digital del token almacenada para verificación sin exponer el contenido original. |
| **ScanEvent**   | Evento de escaneo de QR que registra resultado, agente, fecha y evidencia.               |
| **KPI**         | Key Performance Indicator. Métrica agregada de gestión y operación.                      |

Ontologia:

\<?xml version="1.0" encoding="UTF-8"?\>

\<!DOCTYPE rdf:RDF \[

\<!ENTITY owl "http://www.w3.org/2002/07/owl#"\>

\<!ENTITY rdf "http://www.w3.org/1999/02/22-rdf-syntax-ns#"\>

\<!ENTITY rdfs "http://www.w3.org/2000/01/rdf-schema#"\>

\<!ENTITY xsd "http://www.w3.org/2001/XMLSchema#"\>

\<!ENTITY dc "http://purl.org/dc/elements/1.1/"\>

\<!ENTITY dcterms "http://purl.org/dc/terms/"\>

\<!ENTITY telconet "http://ontology.telconet.ec/datacenter-access#"\>

\]\>

\<rdf:RDF

xmlns:owl="&owl;"

xmlns:rdf="&rdf;"

xmlns:rdfs="&rdfs;"

xmlns:xsd="&xsd;"

xmlns:dc="&dc;"

xmlns:dcterms="&dcterms;"

xmlns:telconet="&telconet;"

xml:base="http://ontology.telconet.ec/datacenter-access"\>

\<!-- ═══════════════════════════════════════════════════════════════

ONTOLOGY METADATA

═══════════════════════════════════════════════════════════════ --\>

\<owl:Ontology rdf:about="http://ontology.telconet.ec/datacenter-access"\>

\<dc:title xml:lang="es"\>Ontología de Gestión de Accesos Físicos a Data Centers\</dc:title\>

\<dc:description xml:lang="es"\>

Mapa ontológico formal (OWL 2) de la Plataforma Multi-Tenant de Gestión de Accesos

Físicos a Data Centers de Telconet LATAM. Define las entidades del dominio, sus

propiedades, relaciones, restricciones y jerarquías derivadas del documento DERCAS v1.0

y los Casos de Uso CU-01 a CU-08.

\</dc:description\>

\<dc:creator\>Telconet LATAM — Área de DataCenter\</dc:creator\>

\<dc:date\>2026-03-05\</dc:date\>

\<owl:versionInfo\>1.0.0\</owl:versionInfo\>

\<dc:subject xml:lang="es"\>Control de acceso físico, Data Centers, Multi-Tenant, QR criptográfico\</dc:subject\>

\<dc:rights xml:lang="es"\>Telconet LATAM — Documento Confidencial\</dc:rights\>

\<!-- Reglas de negocio (migradas desde owl:Axiom para compatibilidad con OWLAPI/WebVOWL) --\>

\<rdfs:comment xml:lang="es"\>RN: Aislamiento Multi-Tenant — Toda entidad sensible debe incorporar tenant_id y/o datacenter_id.

La visibilidad de datos se garantiza mediante Row Level Security (RLS)

a nivel de base de datos, filtrando automáticamente por el contexto

del usuario autenticado.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Inmutabilidad de Auditoría — Los registros de RegistroAuditoria son inmutables. No pueden ser

modificados ni eliminados. Incluyen estado anterior (before) y

estado nuevo (after) para trazabilidad completa.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Token QR de Uso Único — Un QRToken solo puede ser utilizado una vez (usado = true es irreversible).

La validación requiere: firma criptográfica válida, no expirado, no usado,

horario dentro del rango aprobado, y DC correcto.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Cédula Única por Tenant — La cédula de identidad de un Trabajador debe ser única dentro del

contexto de su tenant propietario. La validación incluye formato

ecuatoriano (10 dígitos) y dígito verificador.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Horario Futuro Obligatorio — Al crear una SolicitudAcceso, tanto horarioInicio como horarioFin

deben ser estrictamente futuros respecto al momento de creación,

y horarioFin debe ser posterior a horarioInicio.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Denegación con Motivo Obligatorio — Toda denegación de solicitud requiere un motivoDenegacion no vacío.

El comentarioAprobador es obligatorio tanto para aprobación como denegación.\</rdfs:comment\>

\<rdfs:comment xml:lang="es"\>RN: Eliminación Lógica — La eliminación física de entidades no está permitida en el sistema.

Todas las entidades utilizan desactivación lógica (status = Inactivo)

para mantener integridad referencial e histórica.\</rdfs:comment\>

\</owl:Ontology\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES SUPERIORES (TAXONOMÍA RAÍZ)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Entidad Organizacional ─── --\>

\<owl:Class rdf:about="&telconet;EntidadOrganizacional"\>

\<rdfs:label xml:lang="es"\>Entidad Organizacional\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Clase abstracta que agrupa las entidades que representan unidades organizativas

dentro de la plataforma: tenants, data centers e infraestructura física.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Entidad Operativa ─── --\>

\<owl:Class rdf:about="&telconet;EntidadOperativa"\>

\<rdfs:label xml:lang="es"\>Entidad Operativa\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Clase abstracta que agrupa las entidades que representan procesos operativos

del sistema: solicitudes, tokens, escaneos y registros de visita.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Entidad de Seguridad ─── --\>

\<owl:Class rdf:about="&telconet;EntidadDeSeguridad"\>

\<rdfs:label xml:lang="es"\>Entidad de Seguridad\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Clase abstracta que agrupa las entidades del modelo de identidad, autenticación,

autorización y auditoría (RBAC, permisos, scopes, logs).

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Persona ─── --\>

\<owl:Class rdf:about="&telconet;Persona"\>

\<rdfs:label xml:lang="es"\>Persona\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Clase abstracta que representa a cualquier individuo humano que interactúa

directa o indirectamente con el sistema.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Documento Adjunto ─── --\>

\<owl:Class rdf:about="&telconet;DocumentoAdjunto"\>

\<rdfs:label xml:lang="es"\>Documento Adjunto\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Clase abstracta que agrupa archivos digitales que se adjuntan a entidades

del sistema como soporte documental.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — MODELO ORGANIZACIONAL

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Tenant ─── --\>

\<owl:Class rdf:about="&telconet;Tenant"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOrganizacional"/\>

\<rdfs:label xml:lang="es"\>Tenant (Empresa Cliente)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Organización cliente que contrata servicios de colocación en Data Centers

de Telconet. Representa la unidad de aislamiento lógico multi-tenant.

Cada tenant tiene un identificador UUID v7 y todos sus datos son filtrados

por tenant_id mediante Row Level Security (RLS).

\</rdfs:comment\>

\<!-- Restricción: todo Tenant debe tener al menos un Usuario asignado --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tieneUsuarioAsignado"/\>

\<owl:minCardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:minCardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<!-- Restricción: todo Tenant debe tener un nombre --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;nombre"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<!-- Restricción: todo Tenant debe tener un RUC único --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;ruc"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── DataCenter ─── --\>

\<owl:Class rdf:about="&telconet;DataCenter"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOrganizacional"/\>

\<rdfs:label xml:lang="es"\>Data Center\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Instalación física administrada por Telconet donde se alojan los equipos

de los tenants. Cada DC tiene áreas físicas, un Administrador DC asignado

y agentes de seguridad. Identificado por UUID v7.

\</rdfs:comment\>

\<!-- Restricción: todo DC debe tener ubicación --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;ubicacion"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── Área ─── --\>

\<owl:Class rdf:about="&telconet;Area"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOrganizacional"/\>

\<rdfs:label xml:lang="es"\>Área Física\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Zona física delimitada dentro de un Data Center: sala de servidores, rack,

zona de energía, pasillo frío/caliente. Cada área pertenece a un único DC.

\</rdfs:comment\>

\<!-- Restricción: toda Área pertenece a exactamente un DataCenter --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;perteneceADataCenter"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── TenantAreaAccess ─── --\>

\<owl:Class rdf:about="&telconet;TenantAreaAccess"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOrganizacional"/\>

\<rdfs:label xml:lang="es"\>Acceso de Tenant a Área\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Relación materializada que registra la habilitación de un tenant para

solicitar acceso a un área específica de un Data Center. Incluye datos

de auditoría (quién otorgó el acceso y cuándo).

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;accesoParaTenant"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;accesoAArea"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — MODELO DE PERSONAS

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Usuario ─── --\>

\<owl:Class rdf:about="&telconet;Usuario"\>

\<rdfs:subClassOf rdf:resource="&telconet;Persona"/\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Usuario del Sistema\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Persona con cuenta de acceso al sistema. Posee credenciales, uno o más

roles asignados y un scope de visibilidad (global, datacenter o tenant).

Identificado por UUID v7.

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;email"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tieneRol"/\>

\<owl:minCardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:minCardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── Subclases de Usuario (por Rol/Actor) ─── --\>

\<owl:Class rdf:about="&telconet;AdministradorPlataforma"\>

\<rdfs:subClassOf rdf:resource="&telconet;Usuario"/\>

\<rdfs:label xml:lang="es"\>Administrador de Plataforma\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Usuario con scope global. Gestiona tenants, Data Centers, roles, permisos

y auditoría de toda la plataforma. Acceso total a todos los módulos.

\</rdfs:comment\>

\</owl:Class\>

\<owl:Class rdf:about="&telconet;AdministradorDataCenter"\>

\<rdfs:subClassOf rdf:resource="&telconet;Usuario"/\>

\<rdfs:label xml:lang="es"\>Administrador de Data Center\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Usuario con scope limitado a un Data Center específico. Gestiona solicitudes,

áreas, agentes de seguridad y aprobaciones dentro de su DC.

\</rdfs:comment\>

\<!-- Restricción: está asignado a exactamente un DC --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;administraDataCenter"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<owl:Class rdf:about="&telconet;ClienteTenant"\>

\<rdfs:subClassOf rdf:resource="&telconet;Usuario"/\>

\<rdfs:label xml:lang="es"\>Cliente Telconet (Usuario Tenant)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Usuario con scope de tenant. Gestiona trabajadores, crea solicitudes de

acceso y consulta estados e historial de su empresa.

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;perteneceATenant"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<owl:Class rdf:about="&telconet;AgenteSeguridad"\>

\<rdfs:subClassOf rdf:resource="&telconet;Usuario"/\>

\<rdfs:label xml:lang="es"\>Agente de Seguridad\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Usuario operativo con acceso únicamente a funciones de escaneo QR y

registro de ingresos en el Data Center asignado.

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;asignadoADataCenter"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── Trabajador ─── --\>

\<owl:Class rdf:about="&telconet;Trabajador"\>

\<rdfs:subClassOf rdf:resource="&telconet;Persona"/\>

\<rdfs:label xml:lang="es"\>Trabajador\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Persona física empleada por un tenant que puede ser incluida en solicitudes

de acceso a Data Centers. NO posee cuenta de usuario en el sistema;

es un registro de datos gestionado exclusivamente por su tenant propietario.

La cédula debe ser única dentro de cada tenant.

\</rdfs:comment\>

\<!-- Restricción: pertenece a exactamente un Tenant --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;empleadoDeTenant"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<!-- Restricción: tiene exactamente una cédula --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;cedula"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<!-- Disjunción: un Trabajador NO es un Usuario --\>

\<owl:disjointWith rdf:resource="&telconet;Usuario"/\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — MODELO OPERATIVO (SOLICITUDES Y ACCESOS)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Solicitud de Acceso ─── --\>

\<owl:Class rdf:about="&telconet;SolicitudAcceso"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOperativa"/\>

\<rdfs:label xml:lang="es"\>Solicitud de Acceso (AccessRequest)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Petición formal de un tenant para que un trabajador ingrese a áreas

específicas de un Data Center en una ventana temporal definida.

Ciclo de vida: Pendiente → Aprobada/Denegada → Utilizada/Expirada.

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;solicitadaPorTenant"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;dirigidaADataCenter"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;paraTrabajador"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;solicitaAccesoAAreas"/\>

\<owl:minCardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:minCardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tieneEstadoSolicitud"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── AccessRequestArea (relación materializada) ─── --\>

\<owl:Class rdf:about="&telconet;SolicitudAccesoArea"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOperativa"/\>

\<rdfs:label xml:lang="es"\>Solicitud-Área (AccessRequestArea)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Relación materializada que vincula una solicitud de acceso con cada una

de las áreas físicas solicitadas. Permite la selección múltiple de áreas.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── QR Token ─── --\>

\<owl:Class rdf:about="&telconet;QRToken"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOperativa"/\>

\<rdfs:label xml:lang="es"\>Token QR\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Cadena de datos firmada criptográficamente (RS256) que codifica la

autorización de ingreso físico a un Data Center. Se materializa como

código QR estático. Incluye expiración temporal y validez para un

único ingreso. El hash del token se almacena; nunca el token en texto plano.

\</rdfs:comment\>

\<!-- Restricción: cada QRToken está asociado a exactamente una solicitud --\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tokenDeSolicitud"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tokenHash"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── Evento de Escaneo ─── --\>

\<owl:Class rdf:about="&telconet;EventoEscaneo"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadOperativa"/\>

\<rdfs:label xml:lang="es"\>Evento de Escaneo (AccessScanEvent)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Acción de lectura y validación de un QR por parte de un Agente de

Seguridad en un Data Center. Registra tanto ingresos exitosos como

intentos rechazados, con resultado, observaciones y evidencia.

\</rdfs:comment\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;escaneoDeSolicitud"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;realizadoPorAgente"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\<rdfs:subClassOf\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tieneResultadoEscaneo"/\>

\<owl:cardinality rdf:datatype="&xsd;nonNegativeInteger"\>1\</owl:cardinality\>

\</owl:Restriction\>

\</rdfs:subClassOf\>

\</owl:Class\>

\<!-- ─── Visita (ingreso exitoso) ─── --\>

\<owl:Class rdf:about="&telconet;Visita"\>

\<rdfs:subClassOf rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:label xml:lang="es"\>Visita (Ingreso Exitoso)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Subclase de EventoEscaneo que representa un ingreso físico exitosamente

validado y registrado. Es la base para los reportes de visitas.

\</rdfs:comment\>

\<!-- Equivalencia: una Visita es un EventoEscaneo con resultado VALIDO --\>

\<owl:equivalentClass\>

\<owl:Class\>

\<owl:intersectionOf rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;EventoEscaneo"/\>

\<owl:Restriction\>

\<owl:onProperty rdf:resource="&telconet;tieneResultadoEscaneo"/\>

\<owl:hasValue\>VALIDO\</owl:hasValue\>

\</owl:Restriction\>

\</owl:intersectionOf\>

\</owl:Class\>

\</owl:equivalentClass\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — MODELO DE SEGURIDAD (RBAC)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Rol ─── --\>

\<owl:Class rdf:about="&telconet;Rol"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Rol\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Perfil funcional que agrupa un conjunto de permisos. Los roles se asignan

a usuarios con un scope específico (global, datacenter, tenant).

Modelo RBAC desacoplado para evitar hardcodeo de permisos.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Permiso ─── --\>

\<owl:Class rdf:about="&telconet;Permiso"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Permiso\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Autorización granular para ejecutar una acción específica sobre un módulo

o entidad del sistema. Se asigna a roles, nunca directamente a usuarios.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Scope ─── --\>

\<owl:Class rdf:about="&telconet;Scope"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Scope (Ámbito de Visibilidad)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Delimitador de visibilidad y acción que restringe el contexto operativo

de un rol. Tres niveles: global, datacenter y tenant.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Subclases de Scope ─── --\>

\<owl:Class rdf:about="&telconet;ScopeGlobal"\>

\<rdfs:subClassOf rdf:resource="&telconet;Scope"/\>

\<rdfs:label xml:lang="es"\>Scope Global\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>Visibilidad sobre toda la plataforma (Administrador de Plataforma).\</rdfs:comment\>

\</owl:Class\>

\<owl:Class rdf:about="&telconet;ScopeDataCenter"\>

\<rdfs:subClassOf rdf:resource="&telconet;Scope"/\>

\<rdfs:label xml:lang="es"\>Scope Data Center\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>Visibilidad limitada a un Data Center específico (Admin DC, Agente).\</rdfs:comment\>

\</owl:Class\>

\<owl:Class rdf:about="&telconet;ScopeTenant"\>

\<rdfs:subClassOf rdf:resource="&telconet;Scope"/\>

\<rdfs:label xml:lang="es"\>Scope Tenant\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>Visibilidad limitada a los datos del propio tenant (Cliente).\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Asignación Usuario-Rol (UserRole) ─── --\>

\<owl:Class rdf:about="&telconet;AsignacionUsuarioRol"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Asignación Usuario-Rol (UserRole)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Relación materializada que vincula un usuario con un rol dentro de un scope

específico. Permite que un mismo usuario tenga diferentes roles en diferentes scopes.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Asignación Rol-Permiso (RolePermission) ─── --\>

\<owl:Class rdf:about="&telconet;AsignacionRolPermiso"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Asignación Rol-Permiso (RolePermission)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Relación materializada que vincula un rol con cada uno de los permisos

que lo componen. Granularidad por módulo del sistema.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — DOCUMENTOS Y EVIDENCIA

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Documento de Trabajador ─── --\>

\<owl:Class rdf:about="&telconet;DocumentoTrabajador"\>

\<rdfs:subClassOf rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:label xml:lang="es"\>Documento de Trabajador (WorkerDocument)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Certificación o documento adjunto al perfil de un trabajador que acredita

competencia técnica (certificación eléctrica, seguridad industrial, etc.).

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Documento de Solicitud ─── --\>

\<owl:Class rdf:about="&telconet;DocumentoSolicitud"\>

\<rdfs:subClassOf rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:label xml:lang="es"\>Documento de Solicitud (AccessRequestDocument)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Archivo adjunto a una solicitud de acceso como soporte documental:

orden de trabajo, certificaciones requeridas, permisos especiales.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Evidencia de Escaneo ─── --\>

\<owl:Class rdf:about="&telconet;EvidenciaEscaneo"\>

\<rdfs:subClassOf rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:label xml:lang="es"\>Evidencia de Escaneo (ScanEvidence)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Material fotográfico o textual que complementa el registro de un evento

de escaneo, capturado por el Agente de Seguridad.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — AUDITORÍA Y REPORTES

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Registro de Auditoría ─── --\>

\<owl:Class rdf:about="&telconet;RegistroAuditoria"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Registro de Auditoría (AuditLog)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Registro inmutable de cada acción relevante en el sistema. Contiene:

actor_id, rol, entidad afectada, acción, timestamp, estado anterior

y estado nuevo. Los logs son inmutables y no pueden ser eliminados.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ─── Registro de Exportación de Reporte ─── --\>

\<owl:Class rdf:about="&telconet;RegistroExportacionReporte"\>

\<rdfs:subClassOf rdf:resource="&telconet;EntidadDeSeguridad"/\>

\<rdfs:label xml:lang="es"\>Registro de Exportación (ReportExportLog)\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Log que registra cada exportación de reportes realizada por un usuario:

tipo de reporte, filtros aplicados, formato y cantidad de registros.

\</rdfs:comment\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

CLASES — ENUMERACIONES (ESTADOS Y TIPOS)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Estado de Solicitud ─── --\>

\<owl:Class rdf:about="&telconet;EstadoSolicitud"\>

\<rdfs:label xml:lang="es"\>Estado de Solicitud\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Enumeración del ciclo de vida de una solicitud de acceso.

\</rdfs:comment\>

\<owl:equivalentClass\>

\<owl:Class\>

\<owl:oneOf rdf:parseType="Collection"\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Pendiente"/\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Aprobada"/\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Denegada"/\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Expirada"/\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Utilizada"/\>

\</owl:oneOf\>

\</owl:Class\>

\</owl:equivalentClass\>

\</owl:Class\>

\<!-- Individuos de EstadoSolicitud --\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Pendiente"\>

\<rdfs:label xml:lang="es"\>Pendiente\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>La solicitud ha sido creada y espera revisión del Admin DC.\</rdfs:comment\>

\</telconet:EstadoSolicitud\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Aprobada"\>

\<rdfs:label xml:lang="es"\>Aprobada\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>El Admin DC ha autorizado el acceso; se genera el QR.\</rdfs:comment\>

\</telconet:EstadoSolicitud\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Denegada"\>

\<rdfs:label xml:lang="es"\>Denegada\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>El Admin DC ha rechazado la solicitud con motivo obligatorio.\</rdfs:comment\>

\</telconet:EstadoSolicitud\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Expirada"\>

\<rdfs:label xml:lang="es"\>Expirada\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>El horario_fin se cumplió sin que la solicitud fuera utilizada.\</rdfs:comment\>

\</telconet:EstadoSolicitud\>

\<telconet:EstadoSolicitud rdf:about="&telconet;Utilizada"\>

\<rdfs:label xml:lang="es"\>Utilizada\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>El QR fue escaneado exitosamente y el ingreso fue registrado.\</rdfs:comment\>

\</telconet:EstadoSolicitud\>

\<!-- ─── Resultado de Escaneo ─── --\>

\<owl:Class rdf:about="&telconet;ResultadoEscaneo"\>

\<rdfs:label xml:lang="es"\>Resultado de Escaneo\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>

Enumeración de los posibles resultados al validar un QR escaneado.

\</rdfs:comment\>

\<owl:equivalentClass\>

\<owl:Class\>

\<owl:oneOf rdf:parseType="Collection"\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoValido"/\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoExpirado"/\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoYaUtilizado"/\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoFueraDeHorario"/\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoFirmaInvalida"/\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoDCIncorrecto"/\>

\</owl:oneOf\>

\</owl:Class\>

\</owl:equivalentClass\>

\</owl:Class\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoValido"\>

\<rdfs:label xml:lang="es"\>VÁLIDO\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoExpirado"\>

\<rdfs:label xml:lang="es"\>EXPIRADO\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoYaUtilizado"\>

\<rdfs:label xml:lang="es"\>YA_UTILIZADO\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoFueraDeHorario"\>

\<rdfs:label xml:lang="es"\>FUERA_DE_HORARIO\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoFirmaInvalida"\>

\<rdfs:label xml:lang="es"\>FIRMA_INVÁLIDA\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<telconet:ResultadoEscaneo rdf:about="&telconet;ResultadoDCIncorrecto"\>

\<rdfs:label xml:lang="es"\>DC_INCORRECTO\</rdfs:label\>

\</telconet:ResultadoEscaneo\>

\<!-- ─── Estado Genérico (Activo/Inactivo) ─── --\>

\<owl:Class rdf:about="&telconet;EstadoEntidad"\>

\<rdfs:label xml:lang="es"\>Estado de Entidad\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>Enumeración binaria de estado para tenants, DCs, áreas y trabajadores.\</rdfs:comment\>

\<owl:equivalentClass\>

\<owl:Class\>

\<owl:oneOf rdf:parseType="Collection"\>

\<telconet:EstadoEntidad rdf:about="&telconet;Activo"/\>

\<telconet:EstadoEntidad rdf:about="&telconet;Inactivo"/\>

\</owl:oneOf\>

\</owl:Class\>

\</owl:equivalentClass\>

\</owl:Class\>

\<telconet:EstadoEntidad rdf:about="&telconet;Activo"\>

\<rdfs:label xml:lang="es"\>Activo\</rdfs:label\>

\</telconet:EstadoEntidad\>

\<telconet:EstadoEntidad rdf:about="&telconet;Inactivo"\>

\<rdfs:label xml:lang="es"\>Inactivo\</rdfs:label\>

\</telconet:EstadoEntidad\>

\<!-- ─── Tipo de Acción de Auditoría ─── --\>

\<owl:Class rdf:about="&telconet;TipoAccionAuditoria"\>

\<rdfs:label xml:lang="es"\>Tipo de Acción de Auditoría\</rdfs:label\>

\<rdfs:comment xml:lang="es"\>Catálogo de acciones auditables en el sistema.\</rdfs:comment\>

\<owl:equivalentClass\>

\<owl:Class\>

\<owl:oneOf rdf:parseType="Collection"\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;CREATE_TENANT"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;UPDATE_TENANT"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;CREATE_DATACENTER"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;UPDATE_DATACENTER"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;CREATE_WORKER"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;UPDATE_WORKER"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;CREATE_ACCESS_REQUEST"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;APPROVE_REQUEST"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;DENY_REQUEST"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;GENERATE_QR"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;SCAN_QR"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;VIEW_REPORT"/\>

\<telconet:TipoAccionAuditoria rdf:about="&telconet;EXPORT_REPORT"/\>

\</owl:oneOf\>

\</owl:Class\>

\</owl:equivalentClass\>

\</owl:Class\>

\<!-- ═══════════════════════════════════════════════════════════════

OBJECT PROPERTIES (RELACIONES ENTRE ENTIDADES)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Tenant ↔ Usuario ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tieneUsuarioAsignado"\>

\<rdfs:label xml:lang="es"\>tiene usuario asignado\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&telconet;ClienteTenant"/\>

\<rdfs:comment xml:lang="es"\>Vincula un tenant con sus usuarios tipo Cliente.\</rdfs:comment\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;perteneceATenant"\>

\<rdfs:label xml:lang="es"\>pertenece a tenant\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;ClienteTenant"/\>

\<rdfs:range rdf:resource="&telconet;Tenant"/\>

\<owl:inverseOf rdf:resource="&telconet;tieneUsuarioAsignado"/\>

\</owl:ObjectProperty\>

\<!-- ─── Tenant ↔ Trabajador ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tieneTrabajador"\>

\<rdfs:label xml:lang="es"\>tiene trabajador\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&telconet;Trabajador"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;empleadoDeTenant"\>

\<rdfs:label xml:lang="es"\>empleado de tenant\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Trabajador"/\>

\<rdfs:range rdf:resource="&telconet;Tenant"/\>

\<owl:inverseOf rdf:resource="&telconet;tieneTrabajador"/\>

\</owl:ObjectProperty\>

\<!-- ─── DataCenter ↔ Área ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tieneArea"\>

\<rdfs:label xml:lang="es"\>tiene área\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&telconet;Area"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;perteneceADataCenter"\>

\<rdfs:label xml:lang="es"\>pertenece a Data Center\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Area"/\>

\<rdfs:range rdf:resource="&telconet;DataCenter"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\<owl:inverseOf rdf:resource="&telconet;tieneArea"/\>

\</owl:ObjectProperty\>

\<!-- ─── DataCenter ↔ AdminDC ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;administradoPor"\>

\<rdfs:label xml:lang="es"\>administrado por\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&telconet;AdministradorDataCenter"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;administraDataCenter"\>

\<rdfs:label xml:lang="es"\>administra Data Center\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;AdministradorDataCenter"/\>

\<rdfs:range rdf:resource="&telconet;DataCenter"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\<owl:inverseOf rdf:resource="&telconet;administradoPor"/\>

\</owl:ObjectProperty\>

\<!-- ─── DataCenter ↔ Agente ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tieneAgente"\>

\<rdfs:label xml:lang="es"\>tiene agente de seguridad\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&telconet;AgenteSeguridad"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;asignadoADataCenter"\>

\<rdfs:label xml:lang="es"\>asignado a Data Center\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;AgenteSeguridad"/\>

\<rdfs:range rdf:resource="&telconet;DataCenter"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\<owl:inverseOf rdf:resource="&telconet;tieneAgente"/\>

\</owl:ObjectProperty\>

\<!-- ─── TenantAreaAccess ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;accesoParaTenant"\>

\<rdfs:label xml:lang="es"\>acceso otorgado a tenant\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;TenantAreaAccess"/\>

\<rdfs:range rdf:resource="&telconet;Tenant"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;accesoAArea"\>

\<rdfs:label xml:lang="es"\>acceso a área\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;TenantAreaAccess"/\>

\<rdfs:range rdf:resource="&telconet;Area"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;accesoOtorgadoPor"\>

\<rdfs:label xml:lang="es"\>acceso otorgado por\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;TenantAreaAccess"/\>

\<rdfs:range rdf:resource="&telconet;Usuario"/\>

\</owl:ObjectProperty\>

\<!-- ─── SolicitudAcceso → Tenant, DC, Trabajador ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;solicitadaPorTenant"\>

\<rdfs:label xml:lang="es"\>solicitada por tenant\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;Tenant"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;dirigidaADataCenter"\>

\<rdfs:label xml:lang="es"\>dirigida a Data Center\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;DataCenter"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;paraTrabajador"\>

\<rdfs:label xml:lang="es"\>para trabajador\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;Trabajador"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;solicitaAccesoAAreas"\>

\<rdfs:label xml:lang="es"\>solicita acceso a áreas\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;Area"/\>

\<rdfs:comment xml:lang="es"\>Relación muchos-a-muchos materializada vía SolicitudAccesoArea.\</rdfs:comment\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;aprobadaPor"\>

\<rdfs:label xml:lang="es"\>aprobada por\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;AdministradorDataCenter"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;tieneEstadoSolicitud"\>

\<rdfs:label xml:lang="es"\>tiene estado de solicitud\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;EstadoSolicitud"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;creadaPorUsuario"\>

\<rdfs:label xml:lang="es"\>creada por usuario\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;ClienteTenant"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<!-- ─── QRToken → SolicitudAcceso ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tokenDeSolicitud"\>

\<rdfs:label xml:lang="es"\>token de solicitud\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;QRToken"/\>

\<rdfs:range rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;tieneQRToken"\>

\<rdfs:label xml:lang="es"\>tiene QR token\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&telconet;QRToken"/\>

\<owl:inverseOf rdf:resource="&telconet;tokenDeSolicitud"/\>

\</owl:ObjectProperty\>

\<!-- ─── EventoEscaneo → SolicitudAcceso, Agente ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;escaneoDeSolicitud"\>

\<rdfs:label xml:lang="es"\>escaneo de solicitud\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;realizadoPorAgente"\>

\<rdfs:label xml:lang="es"\>realizado por agente\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&telconet;AgenteSeguridad"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;tieneResultadoEscaneo"\>

\<rdfs:label xml:lang="es"\>tiene resultado de escaneo\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&telconet;ResultadoEscaneo"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;enDataCenter"\>

\<rdfs:label xml:lang="es"\>en Data Center\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&telconet;DataCenter"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<!-- ─── Documentos → Entidades ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;documentoDeTrabajador"\>

\<rdfs:label xml:lang="es"\>documento de trabajador\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DocumentoTrabajador"/\>

\<rdfs:range rdf:resource="&telconet;Trabajador"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;documentoDeSolicitud"\>

\<rdfs:label xml:lang="es"\>documento de solicitud\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DocumentoSolicitud"/\>

\<rdfs:range rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;evidenciaDeEscaneo"\>

\<rdfs:label xml:lang="es"\>evidencia de escaneo\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EvidenciaEscaneo"/\>

\<rdfs:range rdf:resource="&telconet;EventoEscaneo"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<!-- ─── RBAC: Usuario ↔ Rol ↔ Permiso ↔ Scope ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;tieneRol"\>

\<rdfs:label xml:lang="es"\>tiene rol\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Usuario"/\>

\<rdfs:range rdf:resource="&telconet;Rol"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;rolAsignadoAUsuario"\>

\<rdfs:label xml:lang="es"\>rol asignado a usuario\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Rol"/\>

\<rdfs:range rdf:resource="&telconet;Usuario"/\>

\<owl:inverseOf rdf:resource="&telconet;tieneRol"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;rolContienePermiso"\>

\<rdfs:label xml:lang="es"\>rol contiene permiso\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Rol"/\>

\<rdfs:range rdf:resource="&telconet;Permiso"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;permisoEnRol"\>

\<rdfs:label xml:lang="es"\>permiso incluido en rol\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Permiso"/\>

\<rdfs:range rdf:resource="&telconet;Rol"/\>

\<owl:inverseOf rdf:resource="&telconet;rolContienePermiso"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;tieneScope"\>

\<rdfs:label xml:lang="es"\>tiene scope\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;AsignacionUsuarioRol"/\>

\<rdfs:range rdf:resource="&telconet;Scope"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<!-- ─── Auditoría → Actor, Entidad ─── --\>

\<owl:ObjectProperty rdf:about="&telconet;auditoriaRealizadaPor"\>

\<rdfs:label xml:lang="es"\>auditoría realizada por\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroAuditoria"/\>

\<rdfs:range rdf:resource="&telconet;Usuario"/\>

\</owl:ObjectProperty\>

\<owl:ObjectProperty rdf:about="&telconet;tieneAccionAuditoria"\>

\<rdfs:label xml:lang="es"\>tiene acción de auditoría\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroAuditoria"/\>

\<rdfs:range rdf:resource="&telconet;TipoAccionAuditoria"/\>

\<rdf:type rdf:resource="&owl;FunctionalProperty"/\>

\</owl:ObjectProperty\>

\<!-- ═══════════════════════════════════════════════════════════════

DATA PROPERTIES (ATRIBUTOS DE LAS ENTIDADES)

═══════════════════════════════════════════════════════════════ --\>

\<!-- ─── Identificadores ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;id"\>

\<rdfs:label xml:lang="es"\>id (UUID v7)\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Identificador único universal con componente temporal (UUID v7).\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;tenantId"\>

\<rdfs:label xml:lang="es"\>tenant_id (FK)\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Clave foránea de aislamiento multi-tenant. Presente en toda entidad sensible.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;datacenterId"\>

\<rdfs:label xml:lang="es"\>datacenter_id (FK)\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Clave foránea del Data Center. Presente cuando aplica.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Tenant ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;nombre"\>

\<rdfs:label xml:lang="es"\>nombre\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;ruc"\>

\<rdfs:label xml:lang="es"\>RUC / Identificación Fiscal\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Identificador fiscal único de la empresa. Debe ser único en la plataforma.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;contactoNombre"\>

\<rdfs:label xml:lang="es"\>nombre del contacto\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;contactoEmail"\>

\<rdfs:label xml:lang="es"\>email del contacto\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;contactoTelefono"\>

\<rdfs:label xml:lang="es"\>teléfono del contacto\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Tenant"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de DataCenter ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;ubicacion"\>

\<rdfs:label xml:lang="es"\>ubicación\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;ciudad"\>

\<rdfs:label xml:lang="es"\>ciudad\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;pais"\>

\<rdfs:label xml:lang="es"\>país\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DataCenter"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Persona / Trabajador ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;nombres"\>

\<rdfs:label xml:lang="es"\>nombres\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Persona"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;apellidos"\>

\<rdfs:label xml:lang="es"\>apellidos\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Persona"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;cedula"\>

\<rdfs:label xml:lang="es"\>cédula de identidad\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Trabajador"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Documento de identidad ecuatoriano (10 dígitos con dígito verificador). Único por tenant.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;email"\>

\<rdfs:label xml:lang="es"\>correo electrónico\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;telefono"\>

\<rdfs:label xml:lang="es"\>teléfono\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Solicitud de Acceso ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;trabajoARealizar"\>

\<rdfs:label xml:lang="es"\>trabajo a realizar\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;herramientas"\>

\<rdfs:label xml:lang="es"\>herramientas\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;horarioInicio"\>

\<rdfs:label xml:lang="es"\>horario de inicio\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;horarioFin"\>

\<rdfs:label xml:lang="es"\>horario de fin\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;comentarioAprobador"\>

\<rdfs:label xml:lang="es"\>comentario del aprobador\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;motivoDenegacion"\>

\<rdfs:label xml:lang="es"\>motivo de denegación\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Texto obligatorio cuando la solicitud es denegada.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;aprobadoEn"\>

\<rdfs:label xml:lang="es"\>fecha y hora de aprobación\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;SolicitudAcceso"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de QRToken ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;tokenHash"\>

\<rdfs:label xml:lang="es"\>hash del token\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;QRToken"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Huella digital del token. Nunca se almacena el token en texto plano.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;expiraEn"\>

\<rdfs:label xml:lang="es"\>expira en\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;QRToken"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;usado"\>

\<rdfs:label xml:lang="es"\>usado\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;QRToken"/\>

\<rdfs:range rdf:resource="&xsd;boolean"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;usadoEn"\>

\<rdfs:label xml:lang="es"\>usado en (timestamp)\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;QRToken"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de EventoEscaneo ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;fechaEscaneo"\>

\<rdfs:label xml:lang="es"\>fecha de escaneo\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;observaciones"\>

\<rdfs:label xml:lang="es"\>observaciones\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;EventoEscaneo"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Auditoría ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;entidadAfectada"\>

\<rdfs:label xml:lang="es"\>entidad afectada\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroAuditoria"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;estadoAnterior"\>

\<rdfs:label xml:lang="es"\>estado anterior (before)\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroAuditoria"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;estadoNuevo"\>

\<rdfs:label xml:lang="es"\>estado nuevo (after)\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroAuditoria"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Documentos ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;nombreArchivo"\>

\<rdfs:label xml:lang="es"\>nombre del archivo\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;rutaAlmacenamiento"\>

\<rdfs:label xml:lang="es"\>ruta de almacenamiento\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;tipoDocumento"\>

\<rdfs:label xml:lang="es"\>tipo de documento\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;DocumentoAdjunto"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos Temporales Comunes ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;createdAt"\>

\<rdfs:label xml:lang="es"\>fecha de creación\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;updatedAt"\>

\<rdfs:label xml:lang="es"\>fecha de última actualización\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;timestamp"\>

\<rdfs:label xml:lang="es"\>timestamp del evento\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;dateTime"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Estado genérico ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;status"\>

\<rdfs:label xml:lang="es"\>estado\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Estado de la entidad: Activo/Inactivo para entidades organizacionales, ciclo de vida para solicitudes.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;descripcion"\>

\<rdfs:label xml:lang="es"\>descripción\</rdfs:label\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Rol y Permiso ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;nombreRol"\>

\<rdfs:label xml:lang="es"\>nombre del rol\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Rol"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;codigoPermiso"\>

\<rdfs:label xml:lang="es"\>código del permiso\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Permiso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;moduloPermiso"\>

\<rdfs:label xml:lang="es"\>módulo del permiso\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;Permiso"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Módulo del sistema al que aplica el permiso (Dashboard, Empresas, Solicitudes, etc.).\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<!-- ─── Atributos de Exportación ─── --\>

\<owl:DatatypeProperty rdf:about="&telconet;tipoReporte"\>

\<rdfs:label xml:lang="es"\>tipo de reporte\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroExportacionReporte"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;filtrosAplicados"\>

\<rdfs:label xml:lang="es"\>filtros aplicados (JSON)\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroExportacionReporte"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;formatoExportacion"\>

\<rdfs:label xml:lang="es"\>formato de exportación\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroExportacionReporte"/\>

\<rdfs:range rdf:resource="&xsd;string"/\>

\<rdfs:comment xml:lang="es"\>Formato del archivo exportado: CSV, PDF, Excel.\</rdfs:comment\>

\</owl:DatatypeProperty\>

\<owl:DatatypeProperty rdf:about="&telconet;registrosExportados"\>

\<rdfs:label xml:lang="es"\>cantidad de registros exportados\</rdfs:label\>

\<rdfs:domain rdf:resource="&telconet;RegistroExportacionReporte"/\>

\<rdfs:range rdf:resource="&xsd;integer"/\>

\</owl:DatatypeProperty\>

\<!-- ═══════════════════════════════════════════════════════════════

AXIOMAS DE DISJUNCIÓN

═══════════════════════════════════════════════════════════════ --\>

\<!-- Los cuatro tipos de actor-usuario son mutuamente excluyentes --\>

\<owl:AllDisjointClasses\>

\<owl:members rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;AdministradorPlataforma"/\>

\<owl:Class rdf:about="&telconet;AdministradorDataCenter"/\>

\<owl:Class rdf:about="&telconet;ClienteTenant"/\>

\<owl:Class rdf:about="&telconet;AgenteSeguridad"/\>

\</owl:members\>

\</owl:AllDisjointClasses\>

\<!-- Las clases raíz son disjuntas --\>

\<owl:AllDisjointClasses\>

\<owl:members rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;EntidadOrganizacional"/\>

\<owl:Class rdf:about="&telconet;EntidadOperativa"/\>

\<owl:Class rdf:about="&telconet;Persona"/\>

\<owl:Class rdf:about="&telconet;DocumentoAdjunto"/\>

\</owl:members\>

\</owl:AllDisjointClasses\>

\<!-- Los tres tipos de scope son disjuntos --\>

\<owl:AllDisjointClasses\>

\<owl:members rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;ScopeGlobal"/\>

\<owl:Class rdf:about="&telconet;ScopeDataCenter"/\>

\<owl:Class rdf:about="&telconet;ScopeTenant"/\>

\</owl:members\>

\</owl:AllDisjointClasses\>

\<!-- Los tres tipos de documento son disjuntos --\>

\<owl:AllDisjointClasses\>

\<owl:members rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;DocumentoTrabajador"/\>

\<owl:Class rdf:about="&telconet;DocumentoSolicitud"/\>

\<owl:Class rdf:about="&telconet;EvidenciaEscaneo"/\>

\</owl:members\>

\</owl:AllDisjointClasses\>

\<!-- Las entidades organizacionales son disjuntas entre sí --\>

\<owl:AllDisjointClasses\>

\<owl:members rdf:parseType="Collection"\>

\<owl:Class rdf:about="&telconet;Tenant"/\>

\<owl:Class rdf:about="&telconet;DataCenter"/\>

\<owl:Class rdf:about="&telconet;Area"/\>

\<owl:Class rdf:about="&telconet;TenantAreaAccess"/\>

\</owl:members\>

\</owl:AllDisjointClasses\>

\<!-- ═══════════════════════════════════════════════════════════════

ANOTACIONES — REGLAS DE NEGOCIO COMO AXIOMAS SEMÁNTICOS

═══════════════════════════════════════════════════════════════ --\>

\</rdf:RDF\>

**TELCONET LATAM**

Área de DataCenter

**Esquema de Base de Datos**

**y Diccionario de Datos**

Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers

Derivado del Mapa Ontológico OWL 2 — Ontologia_DataCenter_Telconet.owl

Motor: PostgreSQL 16+ con Row Level Security (RLS)

**Marzo 2026**

# 1. Introducción

Este documento define el esquema de base de datos relacional y el diccionario de datos completo para la Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers de Telconet LATAM. Cada tabla ha sido derivada directamente del mapa ontológico OWL 2 (Ontologia_DataCenter_Telconet.owl), manteniendo la trazabilidad clase–tabla–columna.

El esquema está diseñado para PostgreSQL 16+ y contempla: aislamiento multi-tenant mediante Row Level Security (RLS), UUIDs v7 para identificadores principales con optimización de índices temporales, JSONB para snapshots de auditoría (before/after state), y restricciones de integridad referencial completas.

**Convenciones: PK** = Clave Primaria, **FK** = Clave Foránea, **NN** = Not Null, **UQ** = Unique.

# 2. Resumen de Tablas y Trazabilidad Ontológica

| **\#** | **Tabla**                    | **Clase OWL**              | **Categoría**    | **Descripción**                                                        |
|--------|------------------------------|----------------------------|------------------|------------------------------------------------------------------------|
| 1      | **tenants**                  | Tenant                     | Organizacional   | Empresas cliente (organizaciones multi-tenant)                         |
| 2      | **data_centers**             | DataCenter                 | Organizacional   | Instalaciones físicas de Data Center administradas por Telconet        |
| 3      | **areas**                    | Area                       | Organizacional   | Zonas físicas delimitadas dentro de cada Data Center                   |
| 4      | **roles**                    | Rol                        | Seguridad (RBAC) | Perfiles funcionales del modelo RBAC desacoplado                       |
| 5      | **permissions**              | Permiso                    | Seguridad (RBAC) | Autorizaciones granulares por módulo del sistema                       |
| 6      | **role_permissions**         | AsignacionRolPermiso       | Seguridad (RBAC) | Relación N:M entre roles y permisos                                    |
| 7      | **users**                    | Usuario                    | Identidad        | Usuarios del sistema con credenciales y roles asignados                |
| 8      | **user_roles**               | AsignacionUsuarioRol       | Seguridad (RBAC) | Asignación de roles a usuarios con scope específico                    |
| 9      | **tenant_area_access**       | TenantAreaAccess           | Organizacional   | Habilitación de áreas de DC para cada tenant                           |
| 10     | **workers**                  | Trabajador                 | Personas         | Trabajadores de cada empresa cliente (sin cuenta de usuario)           |
| 11     | **worker_documents**         | DocumentoTrabajador        | Documentos       | Certificaciones y documentos adjuntos al perfil del trabajador         |
| 12     | **access_requests**          | SolicitudAcceso            | Operativa        | Solicitudes de ingreso físico a Data Centers                           |
| 13     | **access_request_areas**     | SolicitudAccesoArea        | Operativa        | Relación N:M entre solicitudes y áreas solicitadas                     |
| 14     | **access_request_documents** | DocumentoSolicitud         | Documentos       | Documentos adjuntos a solicitudes de acceso                            |
| 15     | **qr_tokens**                | QRToken                    | Operativa        | Tokens QR firmados criptográficamente para autorización de ingreso     |
| 16     | **access_scan_events**       | EventoEscaneo              | Operativa        | Eventos de escaneo QR por agentes de seguridad (exitosos y rechazados) |
| 17     | **scan_evidence**            | EvidenciaEscaneo           | Documentos       | Evidencia fotográfica adjunta a eventos de escaneo                     |
| 18     | **audit_logs**               | RegistroAuditoria          | Auditoría        | Bitácora inmutable de todas las acciones del sistema                   |
| 19     | **report_export_logs**       | RegistroExportacionReporte | Auditoría        | Registro de exportaciones de reportes realizadas                       |

# 3. Diccionario de Datos

Cada tabla se presenta con su definición completa: columnas, tipos de datos, restricciones, nulabilidad, valores por defecto y descripción funcional.

## 3.1 tenants

| Tabla: **tenants** — Empresas cliente (organizaciones multi-tenant) |                  |                 |          |                    |                                                          |
|---------------------------------------------------------------------|------------------|-----------------|----------|--------------------|----------------------------------------------------------|
| **Columna**                                                         | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**        | **Descripción**                                          |
| **id**                                                              | UUID v7          | **PK**          | No       | uuid_generate_v7() | Identificador único con componente temporal              |
| **name**                                                            | VARCHAR(200)     | **NN** **UQ**   | No       | —                  | Razón social de la empresa cliente                       |
| **ruc**                                                             | VARCHAR(20)      | **NN** **UQ**   | No       | —                  | RUC / Identificación fiscal. Único en toda la plataforma |
| **contacto_nombre**                                                 | VARCHAR(150)     | **NN**          | No       | —                  | Nombre del contacto oficial de la empresa                |
| **contacto_email**                                                  | VARCHAR(200)     | **NN**          | No       | —                  | Email del contacto oficial                               |
| **contacto_telefono**                                               | VARCHAR(20)      |                 | Sí       | —                  | Teléfono del contacto oficial                            |
| **status**                                                          | VARCHAR(20)      | **NN**          | No       | 'ACTIVO'           | Estado: ACTIVO \| INACTIVO                               |
| **created_at**                                                      | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha y hora de creación del registro                    |
| **updated_at**                                                      | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha y hora de última actualización                     |

Clase OWL origen: **telconet:Tenant**

## 3.2 data_centers

| Tabla: **data_centers** — Instalaciones físicas de Data Center administradas por Telconet |                  |                 |          |                    |                                     |
|-------------------------------------------------------------------------------------------|------------------|-----------------|----------|--------------------|-------------------------------------|
| **Columna**                                                                               | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**        | **Descripción**                     |
| **id**                                                                                    | UUID v7          | **PK**          | No       | uuid_generate_v7() | Identificador único del Data Center |
| **name**                                                                                  | VARCHAR(200)     | **NN** **UQ**   | No       | —                  | Nombre del Data Center              |
| **location**                                                                              | VARCHAR(300)     | **NN**          | No       | —                  | Dirección física del DC             |
| **ciudad**                                                                                | VARCHAR(100)     | **NN**          | No       | —                  | Ciudad donde se ubica el DC         |
| **pais**                                                                                  | VARCHAR(100)     | **NN**          | No       | 'Ecuador'          | País donde se ubica el DC           |
| **status**                                                                                | VARCHAR(20)      | **NN**          | No       | 'ACTIVO'           | Estado: ACTIVO \| INACTIVO          |
| **created_at**                                                                            | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha de creación                   |
| **updated_at**                                                                            | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha de última actualización       |

Clase OWL origen: **telconet:DataCenter**

## 3.3 areas

| Tabla: **areas** — Zonas físicas delimitadas dentro de cada Data Center |                  |                 |          |                   |                                                   |
|-------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|---------------------------------------------------|
| **Columna**                                                             | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                   |
| **id**                                                                  | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único del área                      |
| **datacenter_id**                                                       | UUID             | **FK** **NN**   | No       | —                 | FK → data_centers.id. DC al que pertenece el área |
| **name**                                                                | VARCHAR(200)     | **NN**          | No       | —                 | Nombre del área (sala, rack, pasillo)             |
| **descripcion**                                                         | TEXT             |                 | Sí       | —                 | Descripción detallada del área                    |
| **status**                                                              | VARCHAR(20)      | **NN**          | No       | 'ACTIVO'          | Estado: ACTIVO \| INACTIVO                        |
| **created_at**                                                          | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de creación                                 |
| **updated_at**                                                          | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de última actualización                     |

Clase OWL origen: **telconet:Area**

## 3.4 roles

| Tabla: **roles** — Perfiles funcionales del modelo RBAC desacoplado |                  |                 |          |                   |                                                                       |
|---------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-----------------------------------------------------------------------|
| **Columna**                                                         | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                                       |
| **id**                                                              | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único del rol                                           |
| **name**                                                            | VARCHAR(100)     | **NN** **UQ**   | No       | —                 | Nombre del rol: ADMIN_PLATAFORMA, ADMIN_DC, CLIENTE, AGENTE_SEGURIDAD |
| **descripcion**                                                     | TEXT             |                 | Sí       | —                 | Descripción funcional del rol                                         |
| **is_system**                                                       | BOOLEAN          | **NN**          | No       | false             | true si es un rol predefinido del sistema (no editable)               |
| **version**                                                         | INTEGER          | **NN**          | No       | 1                 | Versionado del rol para trazabilidad de cambios                       |
| **created_at**                                                      | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de creación                                                     |
| **updated_at**                                                      | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de última actualización                                         |

Clase OWL origen: **telconet:Rol**

## 3.5 permissions

| Tabla: **permissions** — Autorizaciones granulares por módulo del sistema |                  |                 |          |                   |                                                             |
|---------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------------------------------------------|
| **Columna**                                                               | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                             |
| **id**                                                                    | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único del permiso                             |
| **code**                                                                  | VARCHAR(100)     | **NN** **UQ**   | No       | —                 | Código del permiso: ej. TENANT_CREATE, REQUEST_APPROVE      |
| **module**                                                                | VARCHAR(80)      | **NN**          | No       | —                 | Módulo al que aplica: DASHBOARD, TENANTS, SOLICITUDES, etc. |
| **descripcion**                                                           | TEXT             |                 | Sí       | —                 | Descripción del permiso                                     |
| **created_at**                                                            | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de creación                                           |

Clase OWL origen: **telconet:Permiso**

## 3.6 role_permissions

| Tabla: **role_permissions** — Relación N:M entre roles y permisos |                  |                 |          |                   |                     |
|-------------------------------------------------------------------|------------------|-----------------|----------|-------------------|---------------------|
| **Columna**                                                       | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**     |
| **id**                                                            | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único |
| **role_id**                                                       | UUID             | **FK** **NN**   | No       | —                 | FK → roles.id       |
| **permission_id**                                                 | UUID             | **FK** **NN**   | No       | —                 | FK → permissions.id |
| **granted_at**                                                    | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de asignación |

Clase OWL origen: **telconet:AsignacionRolPermiso**

## 3.7 users

| Tabla: **users** — Usuarios del sistema con credenciales y roles asignados |                  |                 |          |                    |                                                             |
|----------------------------------------------------------------------------|------------------|-----------------|----------|--------------------|-------------------------------------------------------------|
| **Columna**                                                                | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**        | **Descripción**                                             |
| **id**                                                                     | UUID v7          | **PK**          | No       | uuid_generate_v7() | Identificador único del usuario                             |
| **tenant_id**                                                              | UUID             | **FK**          | Sí       | —                  | FK → tenants.id. NULL para Admins Plataforma (scope global) |
| **datacenter_id**                                                          | UUID             | **FK**          | Sí       | —                  | FK → data_centers.id. Para Admin DC y Agentes               |
| **email**                                                                  | VARCHAR(200)     | **NN** **UQ**   | No       | —                  | Email único en toda la plataforma. Credencial de login      |
| **nombre**                                                                 | VARCHAR(150)     | **NN**          | No       | —                  | Nombre completo del usuario                                 |
| **password_hash**                                                          | VARCHAR(255)     | **NN**          | No       | —                  | Hash de la contraseña (bcrypt/argon2)                       |
| **status**                                                                 | VARCHAR(20)      | **NN**          | No       | 'ACTIVO'           | Estado: ACTIVO \| INACTIVO                                  |
| **last_login_at**                                                          | TIMESTAMPTZ      |                 | Sí       | —                  | Fecha del último inicio de sesión                           |
| **created_at**                                                             | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha de creación                                           |
| **updated_at**                                                             | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Fecha de última actualización                               |

Clase OWL origen: **telconet:Usuario**

## 3.8 user_roles

| Tabla: **user_roles** — Asignación de roles a usuarios con scope específico |                  |                 |          |                   |                                                                   |
|-----------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------------------------------------------------|
| **Columna**                                                                 | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                                   |
| **id**                                                                      | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                                               |
| **user_id**                                                                 | UUID             | **FK** **NN**   | No       | —                 | FK → users.id                                                     |
| **role_id**                                                                 | UUID             | **FK** **NN**   | No       | —                 | FK → roles.id                                                     |
| **scope_type**                                                              | VARCHAR(30)      | **NN**          | No       | —                 | Tipo de scope: GLOBAL \| DATACENTER \| TENANT                     |
| **scope_id**                                                                | UUID             |                 | Sí       | —                 | ID del contexto (tenant_id o datacenter_id). NULL si scope GLOBAL |
| **assigned_at**                                                             | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de asignación                                               |
| **assigned_by**                                                             | UUID             | **FK**          | Sí       | —                 | FK → users.id. Usuario que realizó la asignación                  |

Clase OWL origen: **telconet:AsignacionUsuarioRol**

## 3.9 tenant_area_access

| Tabla: **tenant_area_access** — Habilitación de áreas de DC para cada tenant |                  |                 |          |                   |                                                 |
|------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------------------------------|
| **Columna**                                                                  | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                 |
| **id**                                                                       | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                             |
| **tenant_id**                                                                | UUID             | **FK** **NN**   | No       | —                 | FK → tenants.id. Tenant al que se otorga acceso |
| **area_id**                                                                  | UUID             | **FK** **NN**   | No       | —                 | FK → areas.id. Área habilitada para el tenant   |
| **granted_at**                                                               | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha en que se otorgó el acceso                |
| **granted_by**                                                               | UUID             | **FK** **NN**   | No       | —                 | FK → users.id. Admin que otorgó el permiso      |
| **revoked_at**                                                               | TIMESTAMPTZ      |                 | Sí       | —                 | Fecha de revocación (NULL si vigente)           |

Clase OWL origen: **telconet:TenantAreaAccess**

## 3.10 workers

| Tabla: **workers** — Trabajadores de cada empresa cliente (sin cuenta de usuario) |                  |                 |          |                   |                                                                  |
|-----------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|------------------------------------------------------------------|
| **Columna**                                                                       | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                                  |
| **id**                                                                            | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único del trabajador                               |
| **tenant_id**                                                                     | UUID             | **FK** **NN**   | No       | —                 | FK → tenants.id. Tenant propietario (RLS)                        |
| **nombres**                                                                       | VARCHAR(150)     | **NN**          | No       | —                 | Nombres del trabajador                                           |
| **apellidos**                                                                     | VARCHAR(150)     | **NN**          | No       | —                 | Apellidos del trabajador                                         |
| **cedula**                                                                        | VARCHAR(15)      | **NN**          | No       | —                 | Cédula ecuatoriana (10 dígitos). Única por tenant (UQ compuesto) |
| **email**                                                                         | VARCHAR(200)     | **NN**          | No       | —                 | Email del trabajador                                             |
| **telefono**                                                                      | VARCHAR(20)      |                 | Sí       | —                 | Teléfono de contacto                                             |
| **status**                                                                        | VARCHAR(20)      | **NN**          | No       | 'ACTIVO'          | Estado: ACTIVO \| INACTIVO                                       |
| **created_at**                                                                    | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de creación                                                |
| **updated_at**                                                                    | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de última actualización                                    |

Clase OWL origen: **telconet:Trabajador**

## 3.11 worker_documents

| Tabla: **worker_documents** — Certificaciones y documentos adjuntos al perfil del trabajador |                  |                 |          |                   |                                           |
|----------------------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------------------------|
| **Columna**                                                                                  | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                           |
| **id**                                                                                       | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                       |
| **worker_id**                                                                                | UUID             | **FK** **NN**   | No       | —                 | FK → workers.id                           |
| **tenant_id**                                                                                | UUID             | **FK** **NN**   | No       | —                 | FK → tenants.id (RLS)                     |
| **tipo_documento**                                                                           | VARCHAR(80)      | **NN**          | No       | —                 | Tipo: CERTIFICACION, IDENTIFICACION, OTRO |
| **nombre_archivo**                                                                           | VARCHAR(255)     | **NN**          | No       | —                 | Nombre original del archivo subido        |
| **ruta_almacenamiento**                                                                      | VARCHAR(500)     | **NN**          | No       | —                 | Ruta en Object Storage (S3 key)           |
| **mime_type**                                                                                | VARCHAR(100)     |                 | Sí       | —                 | Tipo MIME del archivo                     |
| **file_size_bytes**                                                                          | BIGINT           |                 | Sí       | —                 | Tamaño del archivo en bytes               |
| **uploaded_at**                                                                              | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de carga                            |

Clase OWL origen: **telconet:DocumentoTrabajador**

## 3.12 access_requests

| Tabla: **access_requests** — Solicitudes de ingreso físico a Data Centers |                  |                 |          |                   |                                                            |
|---------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|------------------------------------------------------------|
| **Columna**                                                               | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                            |
| **id**                                                                    | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único de la solicitud                        |
| **tenant_id**                                                             | UUID             | **FK** **NN**   | No       | —                 | FK → tenants.id. Tenant solicitante (RLS)                  |
| **datacenter_id**                                                         | UUID             | **FK** **NN**   | No       | —                 | FK → data_centers.id. DC destino                           |
| **worker_id**                                                             | UUID             | **FK** **NN**   | No       | —                 | FK → workers.id. Trabajador que ingresará                  |
| **trabajo**                                                               | TEXT             | **NN**          | No       | —                 | Descripción del trabajo a realizar                         |
| **herramientas**                                                          | TEXT             |                 | Sí       | —                 | Herramientas que se ingresarán al DC                       |
| **contacto_telefono**                                                     | VARCHAR(20)      | **NN**          | No       | —                 | Teléfono de contacto en sitio                              |
| **contacto_email**                                                        | VARCHAR(200)     | **NN**          | No       | —                 | Email de contacto                                          |
| **horario_inicio**                                                        | TIMESTAMPTZ      | **NN**          | No       | —                 | Inicio de ventana de acceso autorizado                     |
| **horario_fin**                                                           | TIMESTAMPTZ      | **NN**          | No       | —                 | Fin de ventana de acceso autorizado                        |
| **status**                                                                | VARCHAR(20)      | **NN**          | No       | 'PENDIENTE'       | PENDIENTE \| APROBADA \| DENEGADA \| EXPIRADA \| UTILIZADA |
| **aprobado_por**                                                          | UUID             | **FK**          | Sí       | —                 | FK → users.id. Admin DC que aprobó/denegó                  |
| **aprobado_en**                                                           | TIMESTAMPTZ      |                 | Sí       | —                 | Fecha/hora de la decisión                                  |
| **comentario_aprobador**                                                  | TEXT             |                 | Sí       | —                 | Comentario obligatorio del aprobador                       |
| **motivo_denegacion**                                                     | TEXT             |                 | Sí       | —                 | Motivo (obligatorio si status = DENEGADA)                  |
| **created_by**                                                            | UUID             | **FK** **NN**   | No       | —                 | FK → users.id. Cliente que creó la solicitud               |
| **created_at**                                                            | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de creación                                          |
| **updated_at**                                                            | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de última actualización                              |

Clase OWL origen: **telconet:SolicitudAcceso**

## 3.13 access_request_areas

| Tabla: **access_request_areas** — Relación N:M entre solicitudes y áreas solicitadas |                  |                 |          |                   |                         |
|--------------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------|
| **Columna**                                                                          | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**         |
| **id**                                                                               | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único     |
| **request_id**                                                                       | UUID             | **FK** **NN**   | No       | —                 | FK → access_requests.id |
| **area_id**                                                                          | UUID             | **FK** **NN**   | No       | —                 | FK → areas.id           |

Clase OWL origen: **telconet:SolicitudAccesoArea**

## 3.14 access_request_documents

| Tabla: **access_request_documents** — Documentos adjuntos a solicitudes de acceso |                  |                 |          |                   |                                                   |
|-----------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|---------------------------------------------------|
| **Columna**                                                                       | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                   |
| **id**                                                                            | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                               |
| **request_id**                                                                    | UUID             | **FK** **NN**   | No       | —                 | FK → access_requests.id                           |
| **tenant_id**                                                                     | UUID             | **FK** **NN**   | No       | —                 | FK → tenants.id (RLS)                             |
| **nombre_archivo**                                                                | VARCHAR(255)     | **NN**          | No       | —                 | Nombre original del archivo                       |
| **ruta_almacenamiento**                                                           | VARCHAR(500)     | **NN**          | No       | —                 | Ruta en Object Storage (S3 key)                   |
| **tipo**                                                                          | VARCHAR(80)      |                 | Sí       | —                 | ORDEN_TRABAJO \| CERTIFICACION \| PERMISO \| OTRO |
| **mime_type**                                                                     | VARCHAR(100)     |                 | Sí       | —                 | Tipo MIME del archivo                             |
| **uploaded_at**                                                                   | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de carga                                    |

Clase OWL origen: **telconet:DocumentoSolicitud**

## 3.15 qr_tokens

| Tabla: **qr_tokens** — Tokens QR firmados criptográficamente para autorización de ingreso |                  |                      |          |                   |                                                               |
|-------------------------------------------------------------------------------------------|------------------|----------------------|----------|-------------------|---------------------------------------------------------------|
| **Columna**                                                                               | **Tipo de Dato** | **Restricción**      | **Nulo** | **Default**       | **Descripción**                                               |
| **id**                                                                                    | UUID             | **PK**               | No       | gen_random_uuid() | Identificador único del token                                 |
| **request_id**                                                                            | UUID             | **FK** **NN** **UQ** | No       | —                 | FK → access_requests.id. Relación 1:1                         |
| **token_hash**                                                                            | VARCHAR(512)     | **NN** **UQ**        | No       | —                 | Hash SHA-256 del token firmado. Nunca se almacena texto plano |
| **expira_en**                                                                             | TIMESTAMPTZ      | **NN**               | No       | —                 | Expiración = horario_fin de la solicitud                      |
| **usado**                                                                                 | BOOLEAN          | **NN**               | No       | false             | true cuando el QR ha sido escaneado exitosamente              |
| **usado_en**                                                                              | TIMESTAMPTZ      |                      | Sí       | —                 | Timestamp del escaneo exitoso (NULL si no usado)              |
| **qr_image_path**                                                                         | VARCHAR(500)     |                      | Sí       | —                 | Ruta de la imagen QR generada en Object Storage               |
| **invalidated**                                                                           | BOOLEAN          | **NN**               | No       | false             | true si fue invalidado por regeneración                       |
| **created_at**                                                                            | TIMESTAMPTZ      | **NN**               | No       | NOW()             | Fecha de generación                                           |

Clase OWL origen: **telconet:QRToken**

## 3.16 access_scan_events

| Tabla: **access_scan_events** — Eventos de escaneo QR por agentes de seguridad (exitosos y rechazados) |                  |                 |          |                   |                                                                                        |
|--------------------------------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|----------------------------------------------------------------------------------------|
| **Columna**                                                                                            | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                                                        |
| **id**                                                                                                 | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único del evento                                                         |
| **request_id**                                                                                         | UUID             | **FK** **NN**   | No       | —                 | FK → access_requests.id. Solicitud escaneada                                           |
| **agente_id**                                                                                          | UUID             | **FK** **NN**   | No       | —                 | FK → users.id. Agente que realizó el escaneo                                           |
| **datacenter_id**                                                                                      | UUID             | **FK** **NN**   | No       | —                 | FK → data_centers.id. DC donde ocurrió el escaneo                                      |
| **fecha**                                                                                              | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha/hora del escaneo                                                                 |
| **resultado**                                                                                          | VARCHAR(30)      | **NN**          | No       | —                 | VALIDO \| EXPIRADO \| YA_UTILIZADO \| FUERA_HORARIO \| FIRMA_INVALIDA \| DC_INCORRECTO |
| **observaciones**                                                                                      | TEXT             |                 | Sí       | —                 | Observaciones del agente                                                               |

Clase OWL origen: **telconet:EventoEscaneo**

## 3.17 scan_evidence

| Tabla: **scan_evidence** — Evidencia fotográfica adjunta a eventos de escaneo |                  |                 |          |                   |                                     |
|-------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|-------------------------------------|
| **Columna**                                                                   | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                     |
| **id**                                                                        | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                 |
| **scan_event_id**                                                             | UUID             | **FK** **NN**   | No       | —                 | FK → access_scan_events.id          |
| **imagen_ruta**                                                               | VARCHAR(500)     | **NN**          | No       | —                 | Ruta en Object Storage de la imagen |
| **mime_type**                                                                 | VARCHAR(100)     |                 | Sí       | —                 | Tipo MIME de la imagen              |
| **uploaded_at**                                                               | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de carga                      |

Clase OWL origen: **telconet:EvidenciaEscaneo**

## 3.18 audit_logs

| Tabla: **audit_logs** — Bitácora inmutable de todas las acciones del sistema |                  |                 |          |                    |                                                                        |
|------------------------------------------------------------------------------|------------------|-----------------|----------|--------------------|------------------------------------------------------------------------|
| **Columna**                                                                  | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**        | **Descripción**                                                        |
| **id**                                                                       | UUID v7          | **PK**          | No       | uuid_generate_v7() | Identificador único del log (temporal para particionamiento)           |
| **actor_id**                                                                 | UUID             | **FK** **NN**   | No       | —                  | FK → users.id. Usuario que realizó la acción                           |
| **actor_rol**                                                                | VARCHAR(50)      | **NN**          | No       | —                  | Rol del actor al momento de la acción                                  |
| **entidad**                                                                  | VARCHAR(80)      | **NN**          | No       | —                  | Nombre de la entidad afectada: Tenant, DataCenter, AccessRequest, etc. |
| **entidad_id**                                                               | UUID             | **NN**          | No       | —                  | ID del registro afectado                                               |
| **accion**                                                                   | VARCHAR(50)      | **NN**          | No       | —                  | CREATE_TENANT, APPROVE_REQUEST, SCAN_QR, etc.                          |
| **estado_anterior**                                                          | JSONB            |                 | Sí       | —                  | Snapshot JSON del estado antes del cambio (before)                     |
| **estado_nuevo**                                                             | JSONB            |                 | Sí       | —                  | Snapshot JSON del estado después del cambio (after)                    |
| **tenant_id**                                                                | UUID             |                 | Sí       | —                  | Contexto tenant (para filtrado RLS)                                    |
| **datacenter_id**                                                            | UUID             |                 | Sí       | —                  | Contexto datacenter (para filtrado)                                    |
| **ip_address**                                                               | INET             |                 | Sí       | —                  | Dirección IP del cliente                                               |
| **user_agent**                                                               | TEXT             |                 | Sí       | —                  | User-Agent del navegador/cliente                                       |
| **timestamp**                                                                | TIMESTAMPTZ      | **NN**          | No       | NOW()              | Momento exacto de la acción                                            |

Clase OWL origen: **telconet:RegistroAuditoria**

## 3.19 report_export_logs

| Tabla: **report_export_logs** — Registro de exportaciones de reportes realizadas |                  |                 |          |                   |                                                          |
|----------------------------------------------------------------------------------|------------------|-----------------|----------|-------------------|----------------------------------------------------------|
| **Columna**                                                                      | **Tipo de Dato** | **Restricción** | **Nulo** | **Default**       | **Descripción**                                          |
| **id**                                                                           | UUID             | **PK**          | No       | gen_random_uuid() | Identificador único                                      |
| **user_id**                                                                      | UUID             | **FK** **NN**   | No       | —                 | FK → users.id. Usuario que exportó                       |
| **tipo_reporte**                                                                 | VARCHAR(80)      | **NN**          | No       | —                 | Tipo: VISITAS_DIARIO, VISITAS_MENSUAL, CONSOLIDADO, etc. |
| **filtros_aplicados**                                                            | JSONB            |                 | Sí       | —                 | Filtros aplicados en formato JSON                        |
| **formato**                                                                      | VARCHAR(10)      | **NN**          | No       | —                 | CSV \| PDF \| XLSX                                       |
| **registros_exportados**                                                         | INTEGER          |                 | Sí       | —                 | Cantidad de registros en la exportación                  |
| **timestamp**                                                                    | TIMESTAMPTZ      | **NN**          | No       | NOW()             | Fecha de la exportación                                  |

Clase OWL origen: **telconet:RegistroExportacionReporte**

# 4. Relaciones entre Tablas

Todas las relaciones están implementadas como claves foráneas (FOREIGN KEY) con integridad referencial. La cardinalidad se indica como N:1 (muchos a uno) o 1:1 (uno a uno).

| **Tabla Origen**             | **Cardinalidad** | **Tabla Destino**      | **Columna FK**                      | **Descripción**                                |
|------------------------------|------------------|------------------------|-------------------------------------|------------------------------------------------|
| **areas**                    | **N:1**          | **data_centers**       | areas.datacenter_id                 | Cada área pertenece a un único DC              |
| **tenant_area_access**       | **N:1**          | **tenants**            | tenant_area_access.tenant_id        | Acceso otorgado al tenant                      |
| **tenant_area_access**       | **N:1**          | **areas**              | tenant_area_access.area_id          | Área habilitada para el tenant                 |
| **tenant_area_access**       | **N:1**          | **users**              | tenant_area_access.granted_by       | Admin que otorgó el acceso                     |
| **users**                    | **N:1**          | **tenants**            | users.tenant_id                     | Usuario pertenece a un tenant (NULL si global) |
| **users**                    | **N:1**          | **data_centers**       | users.datacenter_id                 | Usuario asignado a un DC (Admin DC, Agente)    |
| **user_roles**               | **N:1**          | **users**              | user_roles.user_id                  | Asignación de rol al usuario                   |
| **user_roles**               | **N:1**          | **roles**              | user_roles.role_id                  | Rol asignado                                   |
| **role_permissions**         | **N:1**          | **roles**              | role_permissions.role_id            | Rol que contiene el permiso                    |
| **role_permissions**         | **N:1**          | **permissions**        | role_permissions.permission_id      | Permiso incluido en el rol                     |
| **workers**                  | **N:1**          | **tenants**            | workers.tenant_id                   | Trabajador empleado del tenant (RLS)           |
| **worker_documents**         | **N:1**          | **workers**            | worker_documents.worker_id          | Documento adjunto al trabajador                |
| **access_requests**          | **N:1**          | **tenants**            | access_requests.tenant_id           | Solicitud del tenant (RLS)                     |
| **access_requests**          | **N:1**          | **data_centers**       | access_requests.datacenter_id       | DC destino de la solicitud                     |
| **access_requests**          | **N:1**          | **workers**            | access_requests.worker_id           | Trabajador que ingresará                       |
| **access_requests**          | **N:1**          | **users**              | access_requests.aprobado_por        | Admin DC que aprobó/denegó                     |
| **access_requests**          | **N:1**          | **users**              | access_requests.created_by          | Cliente que creó la solicitud                  |
| **access_request_areas**     | **N:1**          | **access_requests**    | access_request_areas.request_id     | Solicitud asociada                             |
| **access_request_areas**     | **N:1**          | **areas**              | access_request_areas.area_id        | Área solicitada                                |
| **access_request_documents** | **N:1**          | **access_requests**    | access_request_documents.request_id | Documento adjunto a solicitud                  |
| **qr_tokens**                | **1:1**          | **access_requests**    | qr_tokens.request_id                | Token QR de la solicitud aprobada              |
| **access_scan_events**       | **N:1**          | **access_requests**    | access_scan_events.request_id       | Solicitud escaneada                            |
| **access_scan_events**       | **N:1**          | **users**              | access_scan_events.agente_id        | Agente que escaneó                             |
| **access_scan_events**       | **N:1**          | **data_centers**       | access_scan_events.datacenter_id    | DC del escaneo                                 |
| **scan_evidence**            | **N:1**          | **access_scan_events** | scan_evidence.scan_event_id         | Evidencia del escaneo                          |
| **audit_logs**               | **N:1**          | **users**              | audit_logs.actor_id                 | Actor que ejecutó la acción                    |
| **report_export_logs**       | **N:1**          | **users**              | report_export_logs.user_id          | Usuario que exportó                            |

# 5. Índices

Los índices están diseñados para optimizar las consultas más frecuentes del sistema: filtrado por tenant_id (RLS), búsqueda de solicitudes por DC y estado, validación de QR por hash (\<500ms), y consultas de auditoría cronológica.

| **Tabla**          | **Nombre del Índice**     | **Columna(s)**                             | **Tipo**   | **Propósito**                      |
|--------------------|---------------------------|--------------------------------------------|------------|------------------------------------|
| tenants            | idx_tenants_ruc           | **ruc**                                    | **UNIQUE** | Búsqueda por RUC                   |
| tenants            | idx_tenants_status        | **status**                                 | **BTREE**  | Filtrar tenants activos            |
| data_centers       | idx_dc_status             | **status**                                 | **BTREE**  | Filtrar DC activos                 |
| areas              | idx_areas_dc              | **datacenter_id**                          | **BTREE**  | Áreas por DC                       |
| areas              | idx_areas_dc_name         | **datacenter_id, name**                    | **UNIQUE** | Nombre único de área por DC        |
| workers            | idx_workers_tenant        | **tenant_id**                              | **BTREE**  | Trabajadores por tenant (RLS)      |
| workers            | idx_workers_tenant_cedula | **tenant_id, cedula**                      | **UNIQUE** | Cédula única por tenant            |
| workers            | idx_workers_status        | **tenant_id, status**                      | **BTREE**  | Trabajadores activos por tenant    |
| users              | idx_users_email           | **email**                                  | **UNIQUE** | Email único global                 |
| users              | idx_users_tenant          | **tenant_id**                              | **BTREE**  | Usuarios por tenant (RLS)          |
| users              | idx_users_dc              | **datacenter_id**                          | **BTREE**  | Usuarios por DC                    |
| access_requests    | idx_ar_tenant             | **tenant_id**                              | **BTREE**  | Solicitudes por tenant (RLS)       |
| access_requests    | idx_ar_dc                 | **datacenter_id**                          | **BTREE**  | Solicitudes por DC                 |
| access_requests    | idx_ar_status             | **datacenter_id, status**                  | **BTREE**  | Solicitudes pendientes por DC      |
| access_requests    | idx_ar_horario            | **horario_inicio, horario_fin**            | **BTREE**  | Búsqueda por ventana horaria       |
| access_requests    | idx_ar_worker             | **worker_id**                              | **BTREE**  | Solicitudes por trabajador         |
| qr_tokens          | idx_qr_hash               | **token_hash**                             | **UNIQUE** | Búsqueda rápida por hash (\<500ms) |
| qr_tokens          | idx_qr_request            | **request_id**                             | **UNIQUE** | Token por solicitud (1:1)          |
| qr_tokens          | idx_qr_expira             | **expira_en**                              | **BTREE**  | Tokens por vencer                  |
| access_scan_events | idx_scan_dc_fecha         | **datacenter_id, fecha**                   | **BTREE**  | Escaneos por DC y fecha            |
| access_scan_events | idx_scan_agente           | **agente_id, fecha**                       | **BTREE**  | Actividad de agentes               |
| access_scan_events | idx_scan_request          | **request_id**                             | **BTREE**  | Escaneos por solicitud             |
| audit_logs         | idx_audit_ts              | **timestamp**                              | **BTREE**  | Ordenamiento cronológico           |
| audit_logs         | idx_audit_actor           | **actor_id, timestamp**                    | **BTREE**  | Acciones por usuario               |
| audit_logs         | idx_audit_entidad         | **entidad, entidad_id**                    | **BTREE**  | Logs por entidad                   |
| audit_logs         | idx_audit_tenant          | **tenant_id, timestamp**                   | **BTREE**  | Auditoría por tenant (RLS)         |
| audit_logs         | idx_audit_dc              | **datacenter_id, timestamp**               | **BTREE**  | Auditoría por DC                   |
| tenant_area_access | idx_taa_tenant_area       | **tenant_id, area_id**                     | **UNIQUE** | Acceso único por tenant-área       |
| role_permissions   | idx_rp_role_perm          | **role_id, permission_id**                 | **UNIQUE** | Permiso único por rol              |
| user_roles         | idx_ur_user_role_scope    | **user_id, role_id, scope_type, scope_id** | **UNIQUE** | Asignación única                   |

# 6. Políticas de Row Level Security (RLS)

Las políticas RLS garantizan el aislamiento multi-tenant a nivel de base de datos. Cada consulta se filtra automáticamente por el contexto del usuario autenticado (tenant_id y/o datacenter_id), establecido vía SET app.tenant_id y SET app.datacenter_id al inicio de cada sesión. Los administradores de plataforma operan con políticas BYPASS RLS.

| **Tabla**                    | **Política**             | **Expresión (USING)**                                                                                            | **Descripción**                                           |
|------------------------------|--------------------------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| **tenants**                  | tenant_isolation         | id = current_setting('app.tenant_id')::UUID                                                                      | Aislamiento total: cada tenant solo ve su propio registro |
| **workers**                  | worker_tenant_isolation  | tenant_id = current_setting('app.tenant_id')::UUID                                                               | Trabajadores solo visibles por su tenant propietario      |
| **access_requests**          | request_tenant_isolation | tenant_id = current_setting('app.tenant_id')::UUID OR datacenter_id = current_setting('app.datacenter_id')::UUID | Clientes ven sus solicitudes; Admin DC ve las de su DC    |
| **access_request_areas**     | request_area_isolation   | request_id IN (SELECT id FROM access_requests WHERE tenant_id = current_setting('app.tenant_id')::UUID)          | Hereda aislamiento de access_requests                     |
| **access_request_documents** | request_doc_isolation    | tenant_id = current_setting('app.tenant_id')::UUID                                                               | Documentos solo visibles por el tenant propietario        |
| **worker_documents**         | worker_doc_isolation     | tenant_id = current_setting('app.tenant_id')::UUID                                                               | Documentos de trabajador solo visibles por el tenant      |
| **qr_tokens**                | qr_dc_isolation          | request_id IN (SELECT id FROM access_requests WHERE datacenter_id = current_setting('app.datacenter_id')::UUID)  | QR tokens filtrados por DC del agente/admin               |
| **access_scan_events**       | scan_dc_isolation        | datacenter_id = current_setting('app.datacenter_id')::UUID                                                       | Escaneos solo visibles por el DC donde ocurrieron         |
| **audit_logs**               | audit_scope_isolation    | tenant_id = current_setting('app.tenant_id')::UUID OR datacenter_id = current_setting('app.datacenter_id')::UUID | Logs filtrados por contexto del usuario                   |

# 7. Restricciones y Reglas de Negocio a Nivel de BD

Las siguientes restricciones complementan las claves foráneas y índices únicos. Se implementan como CHECK constraints, triggers o lógica de aplicación según corresponda.

| **Tipo / Tabla**                    | **Expresión / Regla**                                                                                          | **Descripción**                                               |
|-------------------------------------|----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| **CHECK: access_requests**          | horario_fin \> horario_inicio                                                                                  | El fin del horario debe ser posterior al inicio               |
| **CHECK: access_requests**          | horario_inicio \> NOW() (al crear)                                                                             | El horario debe ser futuro al momento de la creación          |
| **CHECK: access_requests**          | status IN ('PENDIENTE','APROBADA','DENEGADA','EXPIRADA','UTILIZADA')                                           | Restricción de valores válidos de estado                      |
| **CHECK: access_requests**          | CASE WHEN status='DENEGADA' THEN motivo_denegacion IS NOT NULL END                                             | Motivo obligatorio si se deniega                              |
| **CHECK: tenants/DC/areas/workers** | status IN ('ACTIVO','INACTIVO')                                                                                | Estados válidos para entidades organizacionales               |
| **CHECK: access_scan_events**       | resultado IN ('VALIDO','EXPIRADO','YA_UTILIZADO','FUERA_HORARIO','FIRMA_INVALIDA','DC_INCORRECTO')             | Valores válidos de resultado de escaneo                       |
| **CHECK: workers.cedula**           | LENGTH(cedula) = 10 AND cedula ~ '^\[0-9\]+\$'                                                                 | Cédula ecuatoriana: 10 dígitos numéricos                      |
| **TRIGGER: audit_logs**             | BEFORE UPDATE OR DELETE → RAISE EXCEPTION                                                                      | Logs inmutables: no se permite UPDATE ni DELETE               |
| **TRIGGER: qr_tokens**              | BEFORE UPDATE SET usado=false WHERE usado=true → RAISE                                                         | El estado usado=true es irreversible                          |
| **TRIGGER: access_requests**        | BEFORE UPDATE WHERE status != 'PENDIENTE' AND OLD.status = 'APROBADA'                                          | No puede modificarse una solicitud tras aprobación            |
| **CRON/Scheduler**                  | UPDATE access_requests SET status='EXPIRADA' WHERE status IN ('PENDIENTE','APROBADA') AND horario_fin \< NOW() | Expiración automática de solicitudes vencidas                 |
| **APP LOGIC**                       | Trabajador.status = 'ACTIVO' al crear solicitud                                                                | No puede crearse solicitud con trabajador inactivo            |
| **APP LOGIC**                       | area_id IN (SELECT area_id FROM tenant_area_access WHERE tenant_id = :tenant)                                  | Áreas seleccionables solo si están habilitadas para el tenant |
| **APP LOGIC**                       | Tenant debe tener ≥ 1 usuario antes de confirmar creación                                                      | No puede existir tenant sin usuario asignado                  |
| **APP LOGIC**                       | Agente.datacenter_id = SolicitudQR.datacenter_id al escanear                                                   | El agente solo puede escanear QR de su DC asignado            |

-- ═══════════════════════════════════════════════════════════════════════════════

-- TELCONET LATAM — Área de DataCenter

-- Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers

--

-- DDL Script — PostgreSQL 16+

-- Derivado del Mapa Ontológico OWL 2: Ontologia_DataCenter_Telconet.owl

-- Fecha: Marzo 2026

-- ═══════════════════════════════════════════════════════════════════════════════

-- Extensiones requeridas

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- gen_random_uuid()

CREATE EXTENSION IF NOT EXISTS "pg_uuidv7"; -- uuid_generate_v7()

-- ─────────────────────────────────────────────────────────────────────────────

-- 1. MODELO ORGANIZACIONAL

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Tenants ───

CREATE TABLE tenants (

id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),

name VARCHAR(200) NOT NULL,

ruc VARCHAR(20) NOT NULL,

contacto_nombre VARCHAR(150) NOT NULL,

contacto_email VARCHAR(200) NOT NULL,

contacto_telefono VARCHAR(20),

status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'

CHECK (status IN ('ACTIVO', 'INACTIVO')),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_tenants_name UNIQUE (name),

CONSTRAINT uq_tenants_ruc UNIQUE (ruc)

);

CREATE INDEX idx_tenants_status ON tenants (status);

-- ─── Data Centers ───

CREATE TABLE data_centers (

id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),

name VARCHAR(200) NOT NULL,

location VARCHAR(300) NOT NULL,

ciudad VARCHAR(100) NOT NULL,

pais VARCHAR(100) NOT NULL DEFAULT 'Ecuador',

status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'

CHECK (status IN ('ACTIVO', 'INACTIVO')),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_dc_name UNIQUE (name)

);

CREATE INDEX idx_dc_status ON data_centers (status);

-- ─── Áreas ───

CREATE TABLE areas (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

datacenter_id UUID NOT NULL REFERENCES data_centers(id) ON DELETE RESTRICT,

name VARCHAR(200) NOT NULL,

descripcion TEXT,

status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'

CHECK (status IN ('ACTIVO', 'INACTIVO')),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_areas_dc_name UNIQUE (datacenter_id, name)

);

CREATE INDEX idx_areas_dc ON areas (datacenter_id);

-- ─────────────────────────────────────────────────────────────────────────────

-- 2. MODELO DE SEGURIDAD (RBAC)

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Roles ───

CREATE TABLE roles (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

name VARCHAR(100) NOT NULL,

descripcion TEXT,

is_system BOOLEAN NOT NULL DEFAULT false,

version INTEGER NOT NULL DEFAULT 1,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_roles_name UNIQUE (name)

);

-- ─── Permisos ───

CREATE TABLE permissions (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

code VARCHAR(100) NOT NULL,

module VARCHAR(80) NOT NULL,

descripcion TEXT,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_permissions_code UNIQUE (code)

);

-- ─── Rol ↔ Permiso ───

CREATE TABLE role_permissions (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,

permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,

granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 3. MODELO DE IDENTIDAD

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Usuarios ───

CREATE TABLE users (

id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),

tenant_id UUID REFERENCES tenants(id) ON DELETE RESTRICT,

datacenter_id UUID REFERENCES data_centers(id) ON DELETE RESTRICT,

email VARCHAR(200) NOT NULL,

nombre VARCHAR(150) NOT NULL,

password_hash VARCHAR(255) NOT NULL,

status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'

CHECK (status IN ('ACTIVO', 'INACTIVO')),

last_login_at TIMESTAMPTZ,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_users_email UNIQUE (email)

);

CREATE INDEX idx_users_tenant ON users (tenant_id);

CREATE INDEX idx_users_dc ON users (datacenter_id);

-- ─── Usuario ↔ Rol (con Scope) ───

CREATE TABLE user_roles (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,

scope_type VARCHAR(30) NOT NULL CHECK (scope_type IN ('GLOBAL', 'DATACENTER', 'TENANT')),

scope_id UUID,

assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

assigned_by UUID REFERENCES users(id),

CONSTRAINT uq_user_role_scope UNIQUE (user_id, role_id, scope_type, scope_id)

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 4. ACCESO TENANT → ÁREAS

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE tenant_area_access (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

area_id UUID NOT NULL REFERENCES areas(id) ON DELETE RESTRICT,

granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

granted_by UUID NOT NULL REFERENCES users(id),

revoked_at TIMESTAMPTZ,

CONSTRAINT uq_tenant_area UNIQUE (tenant_id, area_id)

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 5. MODELO DE PERSONAS

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Trabajadores ───

CREATE TABLE workers (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

nombres VARCHAR(150) NOT NULL,

apellidos VARCHAR(150) NOT NULL,

cedula VARCHAR(15) NOT NULL

CHECK (LENGTH(cedula) = 10 AND cedula ~ '^\[0-9\]+\$'),

email VARCHAR(200) NOT NULL,

telefono VARCHAR(20),

status VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'

CHECK (status IN ('ACTIVO', 'INACTIVO')),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_workers_tenant_cedula UNIQUE (tenant_id, cedula)

);

CREATE INDEX idx_workers_tenant ON workers (tenant_id);

CREATE INDEX idx_workers_status ON workers (tenant_id, status);

-- ─── Documentos de Trabajador ───

CREATE TABLE worker_documents (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,

tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

tipo_documento VARCHAR(80) NOT NULL,

nombre_archivo VARCHAR(255) NOT NULL,

ruta_almacenamiento VARCHAR(500) NOT NULL,

mime_type VARCHAR(100),

file_size_bytes BIGINT,

uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 6. MODELO OPERATIVO

-- ─────────────────────────────────────────────────────────────────────────────

-- ─── Solicitudes de Acceso ───

CREATE TABLE access_requests (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

datacenter_id UUID NOT NULL REFERENCES data_centers(id) ON DELETE RESTRICT,

worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE RESTRICT,

trabajo TEXT NOT NULL,

herramientas TEXT,

contacto_telefono VARCHAR(20) NOT NULL,

contacto_email VARCHAR(200) NOT NULL,

horario_inicio TIMESTAMPTZ NOT NULL,

horario_fin TIMESTAMPTZ NOT NULL,

status VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'

CHECK (status IN ('PENDIENTE','APROBADA','DENEGADA','EXPIRADA','UTILIZADA')),

aprobado_por UUID REFERENCES users(id),

aprobado_en TIMESTAMPTZ,

comentario_aprobador TEXT,

motivo_denegacion TEXT,

created_by UUID NOT NULL REFERENCES users(id),

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT chk_horario_valido CHECK (horario_fin \> horario_inicio),

CONSTRAINT chk_denegacion_motivo CHECK (

CASE WHEN status = 'DENEGADA' THEN motivo_denegacion IS NOT NULL ELSE true END

)

);

CREATE INDEX idx_ar_tenant ON access_requests (tenant_id);

CREATE INDEX idx_ar_dc ON access_requests (datacenter_id);

CREATE INDEX idx_ar_status ON access_requests (datacenter_id, status);

CREATE INDEX idx_ar_horario ON access_requests (horario_inicio, horario_fin);

CREATE INDEX idx_ar_worker ON access_requests (worker_id);

-- ─── Solicitud ↔ Áreas (N:M) ───

CREATE TABLE access_request_areas (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE CASCADE,

area_id UUID NOT NULL REFERENCES areas(id) ON DELETE RESTRICT,

CONSTRAINT uq_request_area UNIQUE (request_id, area_id)

);

-- ─── Documentos de Solicitud ───

CREATE TABLE access_request_documents (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE CASCADE,

tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

nombre_archivo VARCHAR(255) NOT NULL,

ruta_almacenamiento VARCHAR(500) NOT NULL,

tipo VARCHAR(80),

mime_type VARCHAR(100),

uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

-- ─── QR Tokens ───

CREATE TABLE qr_tokens (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE RESTRICT,

token_hash VARCHAR(512) NOT NULL,

expira_en TIMESTAMPTZ NOT NULL,

usado BOOLEAN NOT NULL DEFAULT false,

usado_en TIMESTAMPTZ,

qr_image_path VARCHAR(500),

invalidated BOOLEAN NOT NULL DEFAULT false,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

CONSTRAINT uq_qr_request UNIQUE (request_id),

CONSTRAINT uq_qr_hash UNIQUE (token_hash)

);

CREATE INDEX idx_qr_expira ON qr_tokens (expira_en);

-- ─── Eventos de Escaneo ───

CREATE TABLE access_scan_events (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE RESTRICT,

agente_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

datacenter_id UUID NOT NULL REFERENCES data_centers(id) ON DELETE RESTRICT,

fecha TIMESTAMPTZ NOT NULL DEFAULT NOW(),

resultado VARCHAR(30) NOT NULL

CHECK (resultado IN ('VALIDO','EXPIRADO','YA_UTILIZADO','FUERA_HORARIO','FIRMA_INVALIDA','DC_INCORRECTO')),

observaciones TEXT

);

CREATE INDEX idx_scan_dc_fecha ON access_scan_events (datacenter_id, fecha);

CREATE INDEX idx_scan_agente ON access_scan_events (agente_id, fecha);

CREATE INDEX idx_scan_request ON access_scan_events (request_id);

-- ─── Evidencia de Escaneo ───

CREATE TABLE scan_evidence (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

scan_event_id UUID NOT NULL REFERENCES access_scan_events(id) ON DELETE CASCADE,

imagen_ruta VARCHAR(500) NOT NULL,

mime_type VARCHAR(100),

uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 7. AUDITORÍA

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE audit_logs (

id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),

actor_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

actor_rol VARCHAR(50) NOT NULL,

entidad VARCHAR(80) NOT NULL,

entidad_id UUID NOT NULL,

accion VARCHAR(50) NOT NULL,

estado_anterior JSONB,

estado_nuevo JSONB,

tenant_id UUID,

datacenter_id UUID,

ip_address INET,

user_agent TEXT,

timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

CREATE INDEX idx_audit_ts ON audit_logs (timestamp);

CREATE INDEX idx_audit_actor ON audit_logs (actor_id, timestamp);

CREATE INDEX idx_audit_entidad ON audit_logs (entidad, entidad_id);

CREATE INDEX idx_audit_tenant ON audit_logs (tenant_id, timestamp);

CREATE INDEX idx_audit_dc ON audit_logs (datacenter_id, timestamp);

-- Inmutabilidad de audit_logs

CREATE OR REPLACE FUNCTION prevent_audit_modification()

RETURNS TRIGGER AS \$\$

BEGIN

RAISE EXCEPTION 'Los registros de auditoría son inmutables. No se permite UPDATE ni DELETE.';

RETURN NULL;

END;

\$\$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_immutable

BEFORE UPDATE OR DELETE ON audit_logs

FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ─── Report Export Logs ───

CREATE TABLE report_export_logs (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,

tipo_reporte VARCHAR(80) NOT NULL,

filtros_aplicados JSONB,

formato VARCHAR(10) NOT NULL CHECK (formato IN ('CSV', 'PDF', 'XLSX')),

registros_exportados INTEGER,

timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 8. ROW LEVEL SECURITY (RLS)

-- ─────────────────────────────────────────────────────────────────────────────

-- Habilitar RLS en tablas sensibles

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

ALTER TABLE workers ENABLE ROW LEVEL SECURITY;

ALTER TABLE worker_documents ENABLE ROW LEVEL SECURITY;

ALTER TABLE access_requests ENABLE ROW LEVEL SECURITY;

ALTER TABLE access_request_areas ENABLE ROW LEVEL SECURITY;

ALTER TABLE access_request_documents ENABLE ROW LEVEL SECURITY;

ALTER TABLE qr_tokens ENABLE ROW LEVEL SECURITY;

ALTER TABLE access_scan_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Políticas de aislamiento por tenant

CREATE POLICY tenant_isolation ON tenants

USING (id = current_setting('app.tenant_id')::UUID);

CREATE POLICY worker_tenant_isolation ON workers

USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY worker_doc_isolation ON worker_documents

USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY request_tenant_isolation ON access_requests

USING (

tenant_id = current_setting('app.tenant_id')::UUID

OR datacenter_id = current_setting('app.datacenter_id')::UUID

);

CREATE POLICY request_area_isolation ON access_request_areas

USING (

request_id IN (

SELECT id FROM access_requests

WHERE tenant_id = current_setting('app.tenant_id')::UUID

)

);

CREATE POLICY request_doc_isolation ON access_request_documents

USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY qr_dc_isolation ON qr_tokens

USING (

request_id IN (

SELECT id FROM access_requests

WHERE datacenter_id = current_setting('app.datacenter_id')::UUID

)

);

CREATE POLICY scan_dc_isolation ON access_scan_events

USING (datacenter_id = current_setting('app.datacenter_id')::UUID);

CREATE POLICY audit_scope_isolation ON audit_logs

USING (

tenant_id = current_setting('app.tenant_id')::UUID

OR datacenter_id = current_setting('app.datacenter_id')::UUID

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 9. TRIGGER: Irreversibilidad de QR Token usado

-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_qr_reuse()

RETURNS TRIGGER AS \$\$

BEGIN

IF OLD.usado = true AND NEW.usado = false THEN

RAISE EXCEPTION 'El estado usado=true de un QR Token es irreversible.';

END IF;

RETURN NEW;

END;

\$\$ LANGUAGE plpgsql;

CREATE TRIGGER trg_qr_irreversible

BEFORE UPDATE ON qr_tokens

FOR EACH ROW EXECUTE FUNCTION prevent_qr_reuse();

-- ─────────────────────────────────────────────────────────────────────────────

-- 10. DATOS INICIALES (Roles del Sistema)

-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO roles (name, descripcion, is_system) VALUES

('ADMIN_PLATAFORMA', 'Administrador global de la plataforma Telconet', true),

('ADMIN_DATACENTER', 'Administrador de un Data Center específico', true),

('CLIENTE', 'Usuario tipo Cliente de un tenant', true),

('AGENTE_SEGURIDAD', 'Agente de seguridad de un Data Center', true);

-- ═══════════════════════════════════════════════════════════════════════════════

-- FIN DEL SCRIPT DDL

-- ═══════════════════════════════════════════════════════════════════════════════

**TELCONET LATAM**

Área de DataCenter

**Stack Tecnológico**

Plataforma Multi-Tenant de Gestión de

Accesos Físicos a Data Centers

Versiones verificadas al 5 de marzo de 2026

Fuentes: sitios oficiales, npm, GitHub, endoflife.date

**Marzo 2026**

# 1. Resumen del Stack Tecnológico

El siguiente documento define el stack tecnológico seleccionado para la Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers de Telconet LATAM. Todas las versiones han sido verificadas en sus fuentes oficiales (npm registry, GitHub releases, sitios web de cada proyecto) al 5 de marzo de 2026.

| **Capa**          | **Tecnología**     | **Versión Estable** | **Soporte Hasta** | **Licencia**       |
|-------------------|--------------------|---------------------|-------------------|--------------------|
| **Frontend**      | **Angular**        | 21.1.6              | ~Mayo 2027        | MIT                |
| **Backend / API** | **NestJS**         | 11.1.16             | ~Q3 2026          | MIT                |
| **API Gateway**   | **NestJS Gateway** | 11.1.16             | ~Q3 2026          | MIT                |
| **BD Relacional** | **PostgreSQL**     | 18.3                | ~Sep 2030         | PostgreSQL License |
| **BD Documental** | **MongoDB**        | 8.0.17 GA           | ~Abril 2027       | SSPL               |
| **Runtime**       | **Node.js LTS**    | 24.14.0             | Abril 2028        | MIT                |

# 2. Detalle por Tecnología

## 2.1 Angular (Frontend)

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">Frontend: <strong>Angular</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>21.1.6</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>Angular 21 — Noviembre 2025</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>25 de febrero de 2026</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>Soporte activo (6 meses) + LTS (12 meses) = 18 meses total</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>~Mayo 2027 (LTS)</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• Signal Forms: sistema reactivo moderno que reemplaza Template-Driven y Reactive Forms</p>
<p>• Zoneless por defecto: detección de cambios sin Zone.js, mejor rendimiento y menor bundle</p>
<p>• Vitest como test runner por defecto (reemplaza Karma)</p>
<p>• Build con ESBuild nativo (reemplaza Webpack): builds significativamente más rápidos</p>
<p>• Angular Aria: nueva libreria de UI para accesibilidad (developer preview)</p>
<p>• SSR y SSG mejorados, competitivo con Next.js y Nuxt</p>
<p>• TypeScript 5.5+ con verificación de tipos más estricta</p>
<p>• HttpClient provisto automáticamente en nuevos proyectos</p>
<p>• NgClass en deprecación suave: se recomienda [class.active]="isActive"</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>Node.js 24.x LTS (Krypton) | TypeScript 5.5+</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>Angular 21 es la versión más moderna y estable. Su arquitectura modular, tipado fuerte con TypeScript, y el ecosistema de Angular Material/CDK lo hacen ideal para aplicaciones empresariales multi-tenant como la plataforma de Telconet.</em></td>
</tr>
</tbody>
</table>

## 2.2 NestJS (Backend / Microservicios)

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">Backend / API: <strong>NestJS</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>11.1.16</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>NestJS 11 — Enero 2025</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>5 de marzo de 2026 (publicado hace minutos en npm)</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>Soporte continuo hasta lanzamiento de v12 (~Q3 2026)</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>NestJS 10 entró en EOL con el lanzamiento de v11</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• SWC (Speedy Web Compiler) como compilador por defecto: builds 20x más rápidos</p>
<p>• Vitest como framework de testing por defecto (reemplaza Jest)</p>
<p>• ConsoleLogger mejorado: soporte nativo de JSON logging</p>
<p>• Mejora en generación de opaque keys: arranques más rápidos para módulos dinámicos</p>
<p>• cache-manager v6 con Keyv como interfaz unificada de almacenamiento clave-valor</p>
<p>• ParseDatePipe nativo en @nestjs/common</p>
<p>• Soporte para StandardSchemaValidationPipe (Zod, Valibot sin paquetes adicionales)</p>
<p>• Microservicios: opciones configurables desde el contenedor DI</p>
<p>• IntrinsicException: excepciones que no se auto-loguean</p>
<p>• Observabilidad integrada: Trace IDs propagados automáticamente entre microservicios (Kafka, RabbitMQ, gRPC)</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>Node.js 20.x+ | TypeScript 5.3+</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>NestJS 11 es el estándar de facto para backends empresariales en Node.js. Su arquitectura inspirada en Angular facilita la consistencia con el frontend. Soporte nativo para microservicios, API Gateway pattern, Guards, Interceptors y middleware lo hacen perfecto para la plataforma multi-tenant.</em></td>
</tr>
</tbody>
</table>

## 2.3 NestJS como API Gateway

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">API Gateway: <strong>NestJS (como API Gateway)</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>11.1.16 + @nestjs/microservices 11.x</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>Basado en NestJS 11 con patrón API Gateway</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>5 de marzo de 2026</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>Mismo ciclo que NestJS 11</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>Mismo ciclo que NestJS 11</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• Patrón API Gateway nativo con @nestjs/microservices</p>
<p>• ClientsModule.register() para registro de microservicios por TCP, gRPC, Kafka, RabbitMQ, Redis</p>
<p>• ClientProxy para comunicación request-response y event-based entre servicios</p>
<p>• Soporte para monorepo con Nx o Lerna para organizar gateway + microservicios</p>
<p>• Guards globales para autenticación/autorización centralizada (JWT, RBAC)</p>
<p>• Throttling/Rate Limiting con @nestjs/throttler y Redis como backend</p>
<p>• Interceptors para logging centralizado, transformación de respuestas y circuit breaker</p>
<p>• Exception Filters globales para manejo uniforme de errores</p>
<p>• Health checks con @nestjs/terminus para monitoreo de microservicios</p>
<p>• Swagger/OpenAPI automático con @nestjs/swagger para documentación de la API pública</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>NestJS 11.x | @nestjs/microservices 11.x | Redis (para throttling/cache)</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>Usar NestJS como API Gateway permite mantener un stack homogéneo TypeScript, reutilizar Guards y Decorators del backend, y centralizar autenticación JWT, rate limiting y logging antes de enrutar a los microservicios internos.</em></td>
</tr>
</tbody>
</table>

## 2.4 PostgreSQL (Base de Datos Relacional)

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">Base de Datos Relacional: <strong>PostgreSQL</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>18.3</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>PostgreSQL 18 — Septiembre 2025</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>26 de febrero de 2026</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>Soporte de 5 años desde release inicial</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>~Septiembre 2030</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• Row Level Security (RLS): esencial para aislamiento multi-tenant</p>
<p>• UUIDs v7 nativos con extensión pg_uuidv7: optimización de índices temporales</p>
<p>• JSONB para snapshots de auditoría (before/after state)</p>
<p>• Particionamiento nativo de tablas para audit_logs por fecha</p>
<p>• Mejoras en paralelismo de consultas e índices</p>
<p>• Soporte para GENERATED ALWAYS AS IDENTITY</p>
<p>• Mejoras en lógica de replicación y streaming</p>
<p>• 5 vulnerabilidades de seguridad corregidas en 18.2 (febrero 2026)</p>
<p>• Regresión crítica corregida en 18.3 (out-of-cycle release)</p>
<p>• Compatible con ORMs: TypeORM 0.3+, Prisma 6.x, Sequelize 7.x</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>Almacenamiento SSD recomendado | 4GB+ RAM para índices RLS | Extensiones: pgcrypto, pg_uuidv7</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>PostgreSQL 18 es la versión más estable y segura disponible. Su soporte nativo de RLS es crítico para el aislamiento multi-tenant. JSONB permite auditoría flexible. El ciclo de 5 años de soporte garantiza estabilidad a largo plazo para Telconet.</em></td>
</tr>
</tbody>
</table>

## 2.5 MongoDB (Base de Datos Documental)

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">Base de Datos Documental: <strong>MongoDB</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>8.0.17 (GA Major) / 8.2.5 (Minor Release)</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>MongoDB 8.0 — Octubre 2024 (GA Major on-premises)</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>Febrero 2026</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>30 meses de soporte por Major Release GA</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>MongoDB 8.0: ~Abril 2027 | MongoDB 7.0: ya con soporte extendido</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• 32% más rápido en mezcla 95/5 lectura/escritura vs MongoDB 7.0 (YCSB)</p>
<p>• 200% más rápido en agregaciones de datos time-series</p>
<p>• 50x más rápido en redistribución de datos durante resharding</p>
<p>• Queryable Encryption mejorado para datos sensibles</p>
<p>• Ingress Admission Control: nueva cola de control de admisión</p>
<p>• moveCollection y unshardCollection para gestión flexible de shards</p>
<p>• Corrección de CVE-2025-14847 (MongoBleed) en 8.0.17</p>
<p>• 8.2 Minor Release: disponible para on-premises con mejoras de Search y Vector Search</p>
<p>• Compatible con Mongoose 8.x y driver oficial MongoDB Node.js 6.x</p>
<p>• Ideal para: logs de auditoría de alto volumen, documentos adjuntos metadata, caché de sesiones</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>WiredTiger storage engine | 4GB+ RAM | Replica Set mínimo para producción</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>MongoDB 8.0 complementa a PostgreSQL para casos de uso específicos: almacenamiento de logs de auditoría de alto volumen (append-only), metadata flexible de documentos adjuntos, y caché de sesiones. Su modelo documental permite esquemas flexibles para eventos y configuraciones.</em></td>
</tr>
</tbody>
</table>

## 2.6 Node.js (Runtime)

<table>
<colgroup>
<col style="width: 29%" />
<col style="width: 70%" />
</colgroup>
<thead>
<tr class="header">
<th colspan="2">Runtime: <strong>Node.js</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td><strong>Versión Recomendada</strong></td>
<td><strong>24.14.0 LTS (Krypton)</strong></td>
</tr>
<tr class="even">
<td><strong>Release Mayor</strong></td>
<td><strong>Node.js 24 — Mayo 2025 (Active LTS desde Octubre 2025)</strong></td>
</tr>
<tr class="odd">
<td><strong>Fecha Último Parche</strong></td>
<td><strong>24 de febrero de 2026</strong></td>
</tr>
<tr class="even">
<td><strong>Ciclo de Soporte</strong></td>
<td><strong>Active LTS hasta Octubre 2026 → Maintenance LTS hasta Abril 2028</strong></td>
</tr>
<tr class="odd">
<td><strong>End of Life (EOL)</strong></td>
<td><strong>Abril 2028</strong></td>
</tr>
<tr class="even">
<td colspan="2"><strong>Características Principales</strong></td>
</tr>
<tr class="odd">
<td colspan="2"><blockquote>
<p>• OpenSSL 3.5 con nivel de seguridad 2 por defecto (claves RSA ≥ 2048 bits)</p>
<p>• Validación más estricta de argumentos en APIs de Buffer, fs, timers</p>
<p>• Mejoras en rendimiento de V8 engine</p>
<p>• Soporte completo de ESModules y top-level await</p>
<p>• Corrección de 6 CVEs de seguridad en 24.13.0 (incluido CVE-2026-21637)</p>
<p>• Compatible con NestJS 11, Angular CLI 21, y herramientas de build modernas</p>
</blockquote></td>
</tr>
<tr class="even">
<td><strong>Requisitos</strong></td>
<td>Linux (Ubuntu 22.04+), macOS 13+, Windows 10+</td>
</tr>
<tr class="odd">
<td colspan="2"><strong>Justificación para el Proyecto</strong></td>
</tr>
<tr class="even">
<td colspan="2"><em>Node.js 24 LTS Krypton es la versión Active LTS actual con soporte hasta 2028. Garantía de parches de seguridad y compatibilidad total con NestJS 11 y Angular 21.</em></td>
</tr>
</tbody>
</table>

# 3. Matriz de Compatibilidad

La siguiente tabla muestra la interrelación entre los componentes del stack, sus dependencias y los protocolos de comunicación:

| **Componente**              | **Versión** | **Depende de** | **Protocolo** | **ORM/Driver**        |
|-----------------------------|-------------|----------------|---------------|-----------------------|
| **Angular 21.1.6**          | **21.1.6**  | Node.js 24 LTS | HTTPS         | HttpClient            |
| **NestJS 11 (Backend)**     | **11.1.16** | Node.js 24 LTS | REST/gRPC     | TypeORM/Prisma        |
| **NestJS 11 (API Gateway)** | **11.1.16** | Node.js 24 LTS | TCP/gRPC      | @nestjs/microservices |
| **PostgreSQL**              | **18.3**    | Standalone     | TCP 5432      | TypeORM / pg driver   |
| **MongoDB**                 | **8.0.17**  | Standalone     | TCP 27017     | Mongoose 8.x          |
| **Node.js LTS**             | **24.14.0** | V8 Engine      | N/A           | N/A                   |

# 4. Arquitectura por Capas y Patrones

La siguiente tabla mapea cada capa de la arquitectura con la tecnología seleccionada y su rol específico dentro de la plataforma:

| **Patrón / Capa**      | **Tecnología y Rol**                                                                                                                                             |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Presentación**       | Angular 21 con Signals, standalone components, SSR. Comunicación exclusiva con API Gateway vía HTTPS/REST.                                                       |
| **API Gateway**        | NestJS 11 como punto único de entrada. Centraliza: autenticación JWT (RS256), rate limiting con Redis, logging, CORS, versionado de API y documentación Swagger. |
| **Microservicios**     | NestJS 11 con @nestjs/microservices. Comunicación interna via TCP o gRPC. Cada servicio es independiente y desplegable por separado.                             |
| **Datos Relacionales** | PostgreSQL 18 con RLS para aislamiento multi-tenant. Almacena: tenants, users, solicitudes, QR tokens, RBAC. Transacciones ACID.                                 |
| **Datos Documentales** | MongoDB 8.0 para: audit_logs de alto volumen (append-only), metadata de documentos adjuntos, caché de configuraciones dinámicas, eventos de escaneo masivos.     |
| **Autenticación**      | JWT firmado con RS256. Passport.js integrado en NestJS. Guards para RBAC con scopes (global, datacenter, tenant).                                                |
| **Criptografía QR**    | Node.js crypto module con RS256. Generación de QR con libreria qrcode. Token hash SHA-256 almacenado en PostgreSQL.                                              |
| **Observabilidad**     | NestJS 11 con Trace IDs propagados. OpenTelemetry para trazas distribuidas. Logs JSON nativos del ConsoleLogger mejorado.                                        |

# 5. Recomendaciones de Implementación

> • Monorepo con Nx: Organizar Angular frontend, NestJS API Gateway y NestJS microservicios en un único repositorio con Nx para compartir tipos TypeScript, interfaces y DTOs.
>
> • Contenedorización con Docker: Cada componente (frontend, gateway, microservicios, PostgreSQL, MongoDB, Redis) debe ejecutarse en su propio contenedor para aislamiento y escalabilidad.
>
> • Orquestación con Kubernetes: Para producción, usar Kubernetes con Helm charts para despliegue, escalamiento automático (HPA) y gestión de secretos.
>
> • CI/CD con GitHub Actions o GitLab CI: Pipeline automatizado de build (ESBuild/SWC), test (Vitest), lint, y deploy por ambiente (dev, staging, production).
>
> • Versionado de API: Implementar versionado por URL (/api/v1/) en el API Gateway para permitir evolucón sin romper clientes existentes.
>
> • Monitorización: OpenTelemetry + Grafana/Prometheus para métricas, trazas distribuidas y alertas. Logs JSON del ConsoleLogger de NestJS 11 hacia un stack ELK o Loki.
>
> • Seguridad: HTTPS obligatorio, JWT RS256 con rotación de claves, rate limiting por IP/API key en el Gateway, y CORS estricto configurado por ambiente.
>
> • Migraciones de BD: Usar TypeORM migrations o Prisma migrate para PostgreSQL, y scripts versionados para MongoDB.

**TELCONET LATAM**

Área de DataCenter

**Catálogo de Reglas de Negocio**

**Condiciones IF-THEN**

Para almacenamiento en PostgreSQL 18

Total: 60 reglas extraídas de DERCAS, Casos de Uso y Esquema de BD

**Marzo 2026**

# 1. Resumen Estadístico

Se extrajeron 60 reglas condicionales IF-THEN del documento DERCAS v1.0, los Casos de Uso CU-01 a CU-08 y el Esquema de Base de Datos. Cada regla ha sido catalogada con: código único, categoría, severidad, condición (IF), acción (THEN), alternativa (ELSE), trazabilidad al requerimiento/caso de uso fuente, entidad afectada y tipo de implementación recomendada.

**Por categoría:** VALIDACION (10), INTEGRIDAD DATOS (9), RESTRICCION ACCESO (9), SEGURIDAD (8), EXPIRACION (6), NEGOCIO (5), AUDITORIA (5), TRANSICION ESTADO (4), AISLAMIENTO (2), WORKFLOW (2)

**Por implementación:** APP LOGIC (32), CHECK CONSTRAINT (9), RLS POLICY (5), TRIGGER (4), GUARD (3), COMBINED (2), MIDDLEWARE (2), FRONTEND VALIDATION (2), CRON JOB (1)

**Por capa:** BACKEND (32), DATABASE (18), COMBINED (6), GATEWAY (2), FRONTEND (2)

**Severidad: MANDATORY (58)** \| **WARNING (2)**

# 2. Catálogo Completo de Reglas IF-THEN

Sev: **M** = Mandatory \| **W** = Warning

| **\#** | **Código** | **Categoría**      | **Sev.** | **IF (Condición)**                                                                   | **THEN (Acción) / ELSE**                                                                                                                                           | **Entidad**              | **RF** | **CU** | **Impl.**           |
|--------|------------|--------------------|----------|--------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|--------|--------|---------------------|
| 1      | **BR-001** | INTEGRIDAD DATOS   | **M**    | IF se intenta confirmar la creación de un tenant                                     | THEN verifica que exista ≥1 usuario tipo Cliente asignado. Si existe, permite la creación. *\| ELSE bloquea la confirmación y exige asignación de usuario.*        | **tenants**              | RF-01  | CU-01  | APP LOGIC           |
| 2      | **BR-002** | AISLAMIENTO        | **M**    | IF un usuario consulta entidades sensibles (workers, access_requests, etc.)          | THEN aplica automáticamente filtro RLS WHERE tenant_id = tenant del usuario. *\| ELSE si scope GLOBAL → BYPASS RLS (Admin Plataforma ve todo).*                    | **tenants/\***           | RF-01  | CU-01  | RLS POLICY          |
| 3      | **BR-003** | VALIDACION         | **M**    | IF Admin Plataforma intenta asignar acceso a un área para un tenant                  | THEN verifica que area_id exista, esté ACTIVA y pertenezca a un DC activo. *\| ELSE rechaza: "El área seleccionada no existe o no está activa".*                   | **tenant_area_access**   | RF-01  | CU-01  | APP LOGIC           |
| 4      | **BR-004** | INTEGRIDAD DATOS   | **M**    | IF se intenta crear/editar un tenant con un RUC                                      | THEN verifica unicidad global (UNIQUE constraint tenants.ruc). *\| ELSE rechaza: "Ya existe una empresa con este identificador fiscal".*                           | **tenants**              | RF-01  | CU-01  | CHECK CONSTRAINT    |
| 5      | **BR-005** | TRANSICION ESTADO  | **M**    | IF Admin Plataforma desactiva un tenant (status → INACTIVO)                          | THEN bloquea nuevas solicitudes pero NO elimina datos históricos. *\| ELSE si se reactiva → rehabilita permisos previamente configurados.*                         | **tenants**              | RF-01  | CU-01  | APP LOGIC           |
| 6      | **BR-006** | INTEGRIDAD DATOS   | **M**    | IF se intenta crear un usuario con un email                                          | THEN verifica unicidad global (UNIQUE constraint users.email). *\| ELSE rechaza: "Ya existe un usuario con este correo electrónico".*                              | **users**                | RF-01  | CU-01  | CHECK CONSTRAINT    |
| 7      | **BR-007** | INTEGRIDAD DATOS   | **M**    | IF se crea un área dentro de un Data Center                                          | THEN vincula con FK NOT NULL a un DC + UNIQUE(datacenter_id, name). *\| ELSE rechaza: "Ya existe un área con ese nombre en este DC".*                              | **areas**                | RF-02  | CU-02  | CHECK CONSTRAINT    |
| 8      | **BR-008** | RESTRICCION ACCESO | **M**    | IF usuario con rol ADMIN_DATACENTER accede a información                             | THEN filtra toda info por datacenter_id = scope_id del usuario. *\| ELSE si accede a otro DC → HTTP 403 Forbidden.*                                                | **data_centers**         | RF-02  | CU-02  | GUARD               |
| 9      | **BR-009** | RESTRICCION ACCESO | **M**    | IF Agente escanea un QR                                                              | THEN verifica que datacenter_id del token = datacenter_id del Agente. *\| ELSE resultado DC_INCORRECTO: "Este QR no corresponde a este DC".*                       | **access_scan_events**   | RF-02  | CU-07  | APP LOGIC           |
| 10     | **BR-010** | INTEGRIDAD DATOS   | **M**    | IF se intenta desactivar un área con solicitudes PENDIENTE o APROBADA                | THEN bloquea: "Esta área tiene solicitudes activas". *\| ELSE si no tiene solicitudes activas → permite desactivación lógica.*                                     | **areas**                | RF-02  | CU-02  | APP LOGIC           |
| 11     | **BR-011** | VALIDACION         | **M**    | IF Cliente selecciona un trabajador al crear solicitud                               | THEN verifica worker.status = ACTIVO. Si activo, permite continuar. *\| ELSE bloquea: "Debe seleccionar un trabajador activo".*                                    | **access_requests**      | RF-03  | CU-03  | APP LOGIC           |
| 12     | **BR-012** | VALIDACION         | **M**    | IF se ingresa una cédula al crear/editar trabajador                                  | THEN valida: 10 dígitos numéricos + dígito verificador válido. *\| ELSE muestra: "Formato de cédula inválido".*                                                    | **workers**              | RF-03  | CU-03  | COMBINED            |
| 13     | **BR-013** | INTEGRIDAD DATOS   | **M**    | IF se registra trabajador con cédula dentro de un tenant                             | THEN verifica UNIQUE(tenant_id, cedula). *\| ELSE rechaza: "Ya existe un trabajador con esta cédula en su empresa".*                                               | **workers**              | RF-03  | CU-03  | CHECK CONSTRAINT    |
| 14     | **BR-014** | NEGOCIO            | **M**    | IF se registra un trabajador                                                         | THEN solo crea registro en workers. NO crea registro en users ni credenciales.                                                                                     | **workers**              | RF-03  | CU-03  | APP LOGIC           |
| 15     | **BR-015** | AISLAMIENTO        | **M**    | IF Cliente consulta lista de trabajadores                                            | THEN RLS filtra: solo workers WHERE tenant_id = tenant del usuario. *\| ELSE si otro tenant accede por API a worker de otro → HTTP 404.*                           | **workers**              | RF-03  | CU-03  | RLS POLICY          |
| 16     | **BR-016** | INTEGRIDAD DATOS   | **M**    | IF Cliente edita datos de trabajador existente                                       | THEN permite editar nombres, apellidos, email, tel, status. Cédula = read-only. *\| ELSE si se intenta cambiar cédula por API → ignora o retorna error.*           | **workers**              | RF-03  | CU-03  | APP LOGIC           |
| 17     | **BR-017** | VALIDACION         | **M**    | IF Cliente selecciona áreas al crear solicitud                                       | THEN solo muestra áreas en tenant_area_access para ese tenant + DC, con revoked_at IS NULL. *\| ELSE si fuerza area_id no autorizado por API → HTTP 403.*          | **access_request_areas** | RF-04  | CU-04  | APP LOGIC           |
| 18     | **BR-018** | VALIDACION         | **M**    | IF se crea solicitud con horario_inicio y horario_fin                                | THEN valida que AMBAS fechas \> NOW() al momento de creación. *\| ELSE rechaza: "Las fechas deben ser posteriores al momento actual".*                             | **access_requests**      | RF-04  | CU-04  | COMBINED            |
| 19     | **BR-019** | VALIDACION         | **M**    | IF se definen horario_inicio y horario_fin                                           | THEN CHECK constraint: horario_fin \> horario_inicio. *\| ELSE rechaza: "La fecha de fin debe ser posterior a la de inicio".*                                      | **access_requests**      | RF-04  | CU-04  | CHECK CONSTRAINT    |
| 20     | **BR-020** | TRANSICION ESTADO  | **M**    | IF solicitud tiene status = APROBADA y se intenta modificar campos                   | THEN bloquea UPDATE a campos de contenido (trabajo, herramientas, áreas, horario). *\| ELSE si status = PENDIENTE → campos editables por el Cliente creador.*      | **access_requests**      | RF-04  | CU-04  | TRIGGER             |
| 21     | **BR-021** | TRANSICION ESTADO  | **M**    | IF Cliente crea nueva solicitud de acceso                                            | THEN status = PENDIENTE automáticamente (DEFAULT 'PENDIENTE').                                                                                                     | **access_requests**      | RF-04  | CU-04  | CHECK CONSTRAINT    |
| 22     | **BR-022** | RESTRICCION ACCESO | **M**    | IF usuario de tenant inactivo intenta crear solicitud o trabajador                   | THEN verifica tenant.status = ACTIVO. Si activo, permite. *\| ELSE bloquea y redirige: "Su empresa se encuentra deshabilitada".*                                   | **tenants**              | RF-04  | CU-04  | GUARD               |
| 23     | **BR-023** | VALIDACION         | **M**    | IF Cliente accede a formulario de creación de solicitud                              | THEN selector solo muestra DCs ACTIVOS con áreas habilitadas para el tenant. *\| ELSE si fuerza DC inactivo por API → error "DC no disponible".*                   | **data_centers**         | RF-04  | CU-04  | APP LOGIC           |
| 24     | **BR-024** | RESTRICCION ACCESO | **M**    | IF Admin DC intenta aprobar/denegar solicitud                                        | THEN verifica datacenter_id de solicitud = scope_id del Admin DC. *\| ELSE HTTP 403: "No tiene permisos para gestionar solicitudes de este DC".*                   | **access_requests**      | RF-05  | CU-05  | GUARD               |
| 25     | **BR-025** | VALIDACION         | **M**    | IF Admin DC deniega solicitud (status → DENEGADA)                                    | THEN CHECK: motivo_denegacion IS NOT NULL cuando status = DENEGADA. *\| ELSE bloquea: "Debe ingresar un motivo de denegación".*                                    | **access_requests**      | RF-05  | CU-05  | CHECK CONSTRAINT    |
| 26     | **BR-026** | VALIDACION         | **M**    | IF Admin DC aprueba o deniega solicitud                                              | THEN exige comentario_aprobador NOT NULL/vacío para ambos casos. *\| ELSE bloquea: "El comentario es obligatorio".*                                                | **access_requests**      | RF-05  | CU-05  | APP LOGIC           |
| 27     | **BR-027** | AUDITORIA          | **M**    | IF solicitud es aprobada o denegada                                                  | THEN registra: aprobado_por = user_id, aprobado_en = NOW(), comentario.                                                                                            | **access_requests**      | RF-05  | CU-05  | APP LOGIC           |
| 28     | **BR-028** | WORKFLOW           | **M**    | IF solicitud cambia a APROBADA exitosamente                                          | THEN dispara automáticamente CU-06: genera token RS256, hash, imagen QR, notifica. *\| ELSE si QR falla → solicitud APROBADA + flag error_qr para reintento.*      | **qr_tokens**            | RF-05  | CU-05  | APP LOGIC           |
| 29     | **BR-029** | EXPIRACION         | **M**    | IF Admin DC intenta aprobar solicitud con horario_fin \< NOW()                       | THEN impide aprobación y cambia solicitud a EXPIRADA automáticamente. *\| ELSE si horario_fin \> NOW() → permite aprobación.*                                      | **access_requests**      | RF-05  | CU-05  | APP LOGIC           |
| 30     | **BR-030** | INTEGRIDAD DATOS   | **M**    | IF dos Admin DC procesan la misma solicitud simultáneamente                          | THEN primer UPDATE exitoso cambia status; segundo detecta status ≠ PENDIENTE. *\| ELSE muestra: "Esta solicitud ya fue procesada por otro administrador".*         | **access_requests**      | RF-05  | CU-05  | APP LOGIC           |
| 31     | **BR-031** | SEGURIDAD          | **M**    | IF sistema genera token QR para solicitud aprobada                                   | THEN firma payload con RS256. Almacena SOLO hash SHA-256 del token, NUNCA texto plano.                                                                             | **qr_tokens**            | RF-06  | CU-06  | APP LOGIC           |
| 32     | **BR-032** | EXPIRACION         | **M**    | IF se escanea QR fuera del rango \[horario_inicio, horario_fin\]                     | THEN resultado = FUERA_HORARIO, pantalla roja. *\| ELSE si está dentro del rango → continúa validaciones.*                                                         | **access_scan_events**   | RF-06  | CU-07  | APP LOGIC           |
| 33     | **BR-033** | SEGURIDAD          | **M**    | IF QR escaneado exitosamente (todas validaciones pasan)                              | THEN marca usado=true, usado_en=NOW(). Trigger impide revertir a false. *\| ELSE si ya usado → resultado = YA_UTILIZADO.*                                          | **qr_tokens**            | RF-06  | CU-06  | TRIGGER             |
| 34     | **BR-034** | EXPIRACION         | **M**    | IF se genera QR token                                                                | THEN expira_en = horario_fin de la solicitud asociada.                                                                                                             | **qr_tokens**            | RF-06  | CU-06  | APP LOGIC           |
| 35     | **BR-035** | INTEGRIDAD DATOS   | **M**    | IF se intenta generar QR para solicitud que ya tiene QR válido                       | THEN rechaza (UNIQUE qr_tokens.request_id). *\| ELSE para regenerar → invalidar anterior primero, luego crear nuevo.*                                              | **qr_tokens**            | RF-06  | CU-06  | CHECK CONSTRAINT    |
| 36     | **BR-036** | EXPIRACION         | **M**    | IF solicitud aprobada tiene horario_fin \< NOW() al generar QR                       | THEN NO genera QR y cambia solicitud a EXPIRADA.                                                                                                                   | **qr_tokens**            | RF-06  | CU-06  | APP LOGIC           |
| 37     | **BR-037** | SEGURIDAD          | **M**    | IF Agente escanea QR                                                                 | THEN verifica firma con clave pública RS256. Si válida → continúa. *\| ELSE resultado = FIRMA_INVALIDA, pantalla roja.*                                            | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 38     | **BR-038** | EXPIRACION         | **M**    | IF token del QR tiene expira_en ≤ NOW()                                              | THEN resultado = EXPIRADO, pantalla roja. *\| ELSE si expira_en \> NOW() → continúa siguiente validación.*                                                         | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 39     | **BR-039** | SEGURIDAD          | **M**    | IF token del QR tiene usado = true                                                   | THEN resultado = YA_UTILIZADO, muestra fecha/hora del uso anterior. *\| ELSE si usado = false → continúa siguiente validación.*                                    | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 40     | **BR-040** | RESTRICCION ACCESO | **M**    | IF datacenter_id del token ≠ datacenter_id del Agente                                | THEN resultado = DC_INCORRECTO, pantalla roja. *\| ELSE si coincide → acceso VÁLIDO, pantalla verde.*                                                              | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 41     | **BR-041** | SEGURIDAD          | **M**    | IF cualquier validación del QR falla                                                 | THEN RECHAZA acceso + pantalla roja con motivo + registra AccessScanEvent. *\| ELSE si TODAS pasan → registra ingreso VALIDO + marca token como usado.*            | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 42     | **BR-042** | TRANSICION ESTADO  | **M**    | IF escaneo QR exitoso (resultado = VALIDO)                                           | THEN solicitud → status = UTILIZADA + token → usado=true, usado_en=NOW().                                                                                          | **access_requests**      | RF-07  | CU-07  | APP LOGIC           |
| 43     | **BR-043** | AUDITORIA          | **M**    | IF Agente escanea QR (cualquier resultado)                                           | THEN SIEMPRE crea AccessScanEvent con agente, request, DC, fecha, resultado.                                                                                       | **access_scan_events**   | RF-07  | CU-07  | APP LOGIC           |
| 44     | **BR-044** | RESTRICCION ACCESO | **M**    | IF Admin Plataforma consulta reportes                                                | THEN ve reportes GLOBALES (todos los DC, todos los tenants).                                                                                                       | **access_scan_events**   | RF-08  | CU-08  | RLS POLICY          |
| 45     | **BR-045** | RESTRICCION ACCESO | **M**    | IF Admin DC consulta reportes                                                        | THEN RLS filtra: WHERE datacenter_id = scope_id del Admin DC. *\| ELSE registros de otro DC → ocultos por RLS.*                                                    | **access_scan_events**   | RF-08  | CU-08  | RLS POLICY          |
| 46     | **BR-046** | RESTRICCION ACCESO | **M**    | IF Cliente consulta historial de visitas                                             | THEN filtra por tenant_id → solo visitas de sus trabajadores.                                                                                                      | **access_scan_events**   | RF-08  | CU-08  | RLS POLICY          |
| 47     | **BR-047** | NEGOCIO            | **W**    | IF usuario exporta reporte con \> 10,000 registros                                   | THEN limita a 10,000 o genera exportación asíncrona con notificación. *\| ELSE si ≤ 10,000 → exportación síncrona inmediata.*                                      | **report_export_logs**   | RF-08  | CU-08  | APP LOGIC           |
| 48     | **BR-048** | AUDITORIA          | **M**    | IF usuario exporta reporte en cualquier formato                                      | THEN incluye marca de agua (fecha, usuario) y registra en report_export_logs.                                                                                      | **report_export_logs**   | RF-08  | CU-08  | APP LOGIC           |
| 49     | **BR-049** | AUDITORIA          | **M**    | IF usuario ejecuta acción relevante (CREATE, UPDATE, APPROVE, DENY, SCAN, EXPORT...) | THEN genera registro inmutable en audit_logs con before/after state (JSONB).                                                                                       | **audit_logs**           | —      | —      | APP LOGIC           |
| 50     | **BR-050** | AUDITORIA          | **M**    | IF se intenta UPDATE o DELETE sobre audit_logs                                       | THEN trigger lanza EXCEPTION: "Registros de auditoría son inmutables".                                                                                             | **audit_logs**           | —      | —      | TRIGGER             |
| 51     | **BR-051** | NEGOCIO            | **M**    | IF se intenta DELETE físico en tenants, DCs, áreas, workers, users                   | THEN prohíbe DELETE. Solo UPDATE status = INACTIVO. FK ON DELETE RESTRICT.                                                                                         | **tenants/\***           | —      | —      | APP LOGIC           |
| 52     | **BR-052** | EXPIRACION         | **M**    | IF solicitud tiene status PENDIENTE/APROBADA y horario_fin \< NOW()                  | THEN CRON ejecuta: UPDATE status = EXPIRADA periódicamente.                                                                                                        | **access_requests**      | RF-04  | CU-04  | CRON JOB            |
| 53     | **BR-053** | SEGURIDAD          | **M**    | IF cualquier cliente intenta comunicarse con el sistema                              | THEN toda comunicación sobre HTTPS (TLS 1.2+). HTTP → redirect 301.                                                                                                | **N/A**                  | —      | —      | MIDDLEWARE          |
| 54     | **BR-054** | SEGURIDAD          | **M**    | IF usuario se autentica exitosamente                                                 | THEN emite JWT RS256 con user_id, tenant_id, datacenter_id, roles, scope, exp. *\| ELSE si JWT inválido/expirado → HTTP 401 Unauthorized.*                         | **users**                | —      | —      | MIDDLEWARE          |
| 55     | **BR-055** | RESTRICCION ACCESO | **M**    | IF usuario inicia sesión en frontend                                                 | THEN menú construido dinámicamente según permisos del rol. *\| ELSE módulos sin permiso no se renderizan en el DOM.*                                               | **permissions**          | —      | —      | FRONTEND VALIDATION |
| 56     | **BR-056** | NEGOCIO            | **M**    | IF usuario ejecuta acción crítica (aprobar, denegar, desactivar, revocar)            | THEN muestra diálogo de confirmación obligatorio con descripción de consecuencias. *\| ELSE si cancela → acción no se ejecuta.*                                    | **N/A**                  | —      | —      | FRONTEND VALIDATION |
| 57     | **BR-057** | NEGOCIO            | **M**    | IF Agente escanea QR                                                                 | THEN todo el proceso de validación debe completarse en \< 500ms. Índice UNIQUE en token_hash. *\| ELSE si \> 500ms → registra alerta de rendimiento.*              | **qr_tokens**            | —      | CU-07  | APP LOGIC           |
| 58     | **BR-058** | WORKFLOW           | **W**    | IF Admin Plataforma revoca áreas habilitadas de un tenant                            | THEN notifica al Admin DC sobre solicitudes PENDIENTES con áreas removidas. *\| ELSE solicitudes ya APROBADAS no se afectan retroactivamente.*                     | **tenant_area_access**   | RF-01  | CU-01  | APP LOGIC           |
| 59     | **BR-059** | SEGURIDAD          | **M**    | IF se intenta UPDATE qr_tokens SET usado=false WHERE usado=true                      | THEN trigger lanza EXCEPTION: "Estado usado=true es irreversible".                                                                                                 | **qr_tokens**            | RF-06  | CU-06  | TRIGGER             |
| 60     | **BR-060** | VALIDACION         | **M**    | IF se registra un AccessScanEvent                                                    | THEN resultado IN (VALIDO, EXPIRADO, YA_UTILIZADO, FUERA_HORARIO, FIRMA_INVALIDA, DC_INCORRECTO). *\| ELSE cualquier otro valor → rechazado por CHECK constraint.* | **access_scan_events**   | RF-07  | CU-07  | CHECK CONSTRAINT    |

-- ═══════════════════════════════════════════════════════════════════════════════

-- TELCONET LATAM — Área de DataCenter

-- Plataforma Multi-Tenant de Gestión de Accesos Físicos a Data Centers

--

-- Tabla de Reglas de Negocio Condicionales (IF-THEN)

-- Extraídas de: DERCAS v1.0, Casos de Uso CU-01 a CU-08, Esquema de BD

--

-- Motor: PostgreSQL 18.3

-- Fecha: Marzo 2026

-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────

-- 1. TABLA: business_rules

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS business_rules (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

-- Identificación

rule_code VARCHAR(20) NOT NULL UNIQUE,

rule_name VARCHAR(200) NOT NULL,

-- Clasificación

category VARCHAR(50) NOT NULL

CHECK (category IN (

'VALIDACION', -- Validación de datos de entrada

'RESTRICCION_ACCESO', -- Control de acceso RBAC/Scope

'TRANSICION_ESTADO', -- Cambio de estado en ciclo de vida

'INTEGRIDAD_DATOS', -- Integridad referencial y lógica

'SEGURIDAD', -- Seguridad, criptografía, tokens

'AUDITORIA', -- Reglas de auditoría y trazabilidad

'WORKFLOW', -- Flujo de trabajo / disparadores

'AISLAMIENTO', -- Multi-tenant / RLS

'EXPIRACION', -- Temporalidad, vencimiento

'NEGOCIO' -- Regla de dominio general

)),

severity VARCHAR(20) NOT NULL DEFAULT 'MANDATORY'

CHECK (severity IN ('MANDATORY', 'WARNING', 'INFORMATIONAL')),

-- La regla condicional

condition_if TEXT NOT NULL, -- La condición (IF / CUANDO)

condition_then TEXT NOT NULL, -- La acción/resultado (THEN / ENTONCES)

condition_else TEXT, -- Acción alternativa (ELSE / SI NO) — opcional

-- Trazabilidad al documento fuente

source_document VARCHAR(50) NOT NULL DEFAULT 'DERCAS_v1.0',

source_section VARCHAR(100), -- Sección del documento fuente

source_requirement VARCHAR(20), -- RF-01, RF-02, etc.

source_use_case VARCHAR(20), -- CU-01, CU-02, etc.

-- Entidades afectadas

entity_affected VARCHAR(100) NOT NULL, -- Tabla/entidad principal

related_entities TEXT, -- Otras entidades involucradas

-- Implementación

implementation_type VARCHAR(30) NOT NULL

CHECK (implementation_type IN (

'CHECK_CONSTRAINT', -- CHECK en PostgreSQL

'TRIGGER', -- Trigger en PostgreSQL

'RLS_POLICY', -- Row Level Security

'APP_LOGIC', -- Lógica de aplicación (NestJS)

'GUARD', -- NestJS Guard (RBAC)

'MIDDLEWARE', -- NestJS Middleware

'CRON_JOB', -- Tarea programada

'DB_FUNCTION', -- Función de base de datos

'FRONTEND_VALIDATION', -- Validación en Angular

'COMBINED' -- Múltiples capas

)),

implementation_layer VARCHAR(20) NOT NULL DEFAULT 'BACKEND'

CHECK (implementation_layer IN ('DATABASE', 'BACKEND', 'FRONTEND', 'GATEWAY', 'COMBINED')),

-- Metadata

is_active BOOLEAN NOT NULL DEFAULT true,

version INTEGER NOT NULL DEFAULT 1,

notes TEXT,

created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

-- Índices

CREATE INDEX idx_br_category ON business_rules (category);

CREATE INDEX idx_br_entity ON business_rules (entity_affected);

CREATE INDEX idx_br_source_req ON business_rules (source_requirement);

CREATE INDEX idx_br_source_uc ON business_rules (source_use_case);

CREATE INDEX idx_br_impl_type ON business_rules (implementation_type);

CREATE INDEX idx_br_severity ON business_rules (severity);

CREATE INDEX idx_br_active ON business_rules (is_active);

-- Tabla de relación: regla → entidad(es) afectada(s) para búsqueda cruzada

CREATE TABLE IF NOT EXISTS business_rule_entities (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

rule_id UUID NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,

table_name VARCHAR(80) NOT NULL,

column_name VARCHAR(80),

constraint_type VARCHAR(30),

CONSTRAINT uq_rule_entity UNIQUE (rule_id, table_name, column_name)

);

-- ─────────────────────────────────────────────────────────────────────────────

-- 2. INSERCIÓN DE REGLAS — GESTIÓN DE TENANTS (RF-01 / CU-01)

-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO business_rules (rule_code, rule_name, category, severity, condition_if, condition_then, condition_else, source_section, source_requirement, source_use_case, entity_affected, related_entities, implementation_type, implementation_layer) VALUES

('BR-001', 'Tenant requiere usuario asignado', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se intenta confirmar la creación de un tenant',

'THEN el sistema verifica que exista al menos un usuario tipo Cliente asignado al tenant. Si existe, permite la creación.',

'ELSE el sistema bloquea la confirmación y exige la asignación de al menos un usuario tipo Cliente antes de guardar.',

'RF-01 Criterios de Aceptación', 'RF-01', 'CU-01', 'tenants', 'users', 'APP_LOGIC', 'BACKEND'),

('BR-002', 'Aislamiento de datos por tenant_id', 'AISLAMIENTO', 'MANDATORY',

'IF un usuario autenticado realiza cualquier consulta a entidades sensibles (workers, access_requests, worker_documents, etc.)',

'THEN el sistema aplica automáticamente el filtro RLS WHERE tenant_id = current_setting(''app.tenant_id'')::UUID, mostrando solo datos del tenant del usuario.',

'ELSE si el usuario tiene scope GLOBAL (Admin Plataforma), se aplica BYPASS RLS y puede ver todos los tenants.',

'RF-01 Criterios de Aceptación / Sección 2.1', 'RF-01', 'CU-01', 'tenants', 'workers, access_requests, worker_documents, access_request_documents', 'RLS_POLICY', 'DATABASE'),

('BR-003', 'No asignar acceso a áreas inexistentes', 'VALIDACION', 'MANDATORY',

'IF el Administrador de Plataforma intenta asignar acceso a un área para un tenant',

'THEN el sistema verifica que el area_id exista en la tabla areas, que el área esté en estado ACTIVO y que pertenezca a un DC activo. Si es válida, crea el registro en tenant_area_access.',

'ELSE el sistema rechaza la asignación y muestra el mensaje "El área seleccionada no existe o no está activa".',

'RF-01 Criterios de Aceptación', 'RF-01', 'CU-01', 'tenant_area_access', 'areas, data_centers', 'APP_LOGIC', 'BACKEND'),

('BR-004', 'RUC único en toda la plataforma', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se intenta crear o editar un tenant con un RUC determinado',

'THEN el sistema verifica que no exista otro tenant con el mismo RUC (UNIQUE constraint en tenants.ruc). Si es único, permite la operación.',

'ELSE el sistema rechaza la operación y muestra "Ya existe una empresa con este identificador fiscal".',

'RF-01 / CU-01 EX-01', 'RF-01', 'CU-01', 'tenants', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-005', 'Desactivación de tenant conserva datos históricos', 'TRANSICION_ESTADO', 'MANDATORY',

'IF el Administrador de Plataforma desactiva un tenant (status = INACTIVO)',

'THEN el sistema cambia el status a INACTIVO, bloquea la creación de nuevas solicitudes, pero NO elimina datos históricos (solicitudes, visitas, trabajadores).',

'ELSE (si se reactiva) el sistema cambia status a ACTIVO y rehabilita permisos de acceso previamente configurados.',

'CU-01 FA-02/FA-03', 'RF-01', 'CU-01', 'tenants', 'access_requests, workers', 'APP_LOGIC', 'BACKEND'),

('BR-006', 'Email de usuario único global', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se intenta crear un usuario con un email determinado',

'THEN el sistema verifica unicidad global del email (UNIQUE constraint en users.email). Si es único, permite la creación.',

'ELSE el sistema rechaza y muestra "Ya existe un usuario con este correo electrónico".',

'CU-01 EX-04', 'RF-01', 'CU-01', 'users', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 3. INSERCIÓN DE REGLAS — GESTIÓN DE DATA CENTERS (RF-02 / CU-02)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-007', 'Área pertenece a un único DC', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se crea un área dentro de un Data Center',

'THEN el área se vincula mediante datacenter_id (FK NOT NULL) a exactamente un DC. El nombre del área debe ser único dentro del mismo DC (UNIQUE datacenter_id + name).',

'ELSE si el nombre ya existe en ese DC, el sistema rechaza con "Ya existe un área con ese nombre en este Data Center".',

'RF-02 Criterios de Aceptación', 'RF-02', 'CU-02', 'areas', 'data_centers', 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-008', 'Admin DC solo visualiza su propio DC', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un usuario con rol ADMIN_DATACENTER inicia sesión e intenta acceder a información de Data Centers',

'THEN el sistema filtra toda la información por datacenter_id = scope_id del usuario. Solo puede ver datos de su DC asignado.',

'ELSE si intenta acceder a otro DC por URL o API, el sistema retorna HTTP 403 Forbidden.',

'RF-02 Criterios de Aceptación', 'RF-02', 'CU-02', 'data_centers', 'users, user_roles', 'GUARD', 'BACKEND'),

('BR-009', 'Agente solo escanea QR de su DC', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un Agente de Seguridad intenta escanear un código QR',

'THEN el sistema verifica que el datacenter_id del token QR coincida con el datacenter_id asignado al Agente en su user_roles.scope_id.',

'ELSE si el DC no coincide, el sistema muestra resultado "DC_INCORRECTO" con pantalla roja y mensaje "Este QR no corresponde a este Data Center".',

'RF-02 Criterios de Aceptación / RF-07', 'RF-02', 'CU-07', 'access_scan_events', 'qr_tokens, users, user_roles', 'APP_LOGIC', 'BACKEND'),

('BR-010', 'Área con solicitudes activas no puede eliminarse', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF el Administrador intenta eliminar/desactivar un área que tiene solicitudes en estado PENDIENTE o APROBADA',

'THEN el sistema bloquea la eliminación y muestra "Esta área tiene solicitudes activas. Desactive las solicitudes primero".',

'ELSE si no tiene solicitudes activas, permite la desactivación (status = INACTIVO). Nunca eliminación física.',

'CU-02 FA-03 / EX-02', 'RF-02', 'CU-02', 'areas', 'access_requests, access_request_areas', 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 4. INSERCIÓN DE REGLAS — GESTIÓN DE TRABAJADORES (RF-03 / CU-03)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-011', 'No crear solicitud con trabajador inactivo', 'VALIDACION', 'MANDATORY',

'IF un Cliente intenta crear una solicitud de acceso seleccionando un trabajador',

'THEN el sistema verifica que el trabajador tenga status = ACTIVO. Si está activo, permite continuar con la creación.',

'ELSE si el trabajador tiene status = INACTIVO, el sistema bloquea la creación y muestra "Debe seleccionar un trabajador activo".',

'RF-03 Criterios de Aceptación', 'RF-03', 'CU-03', 'access_requests', 'workers', 'APP_LOGIC', 'COMBINED'),

('BR-012', 'Validar formato de cédula ecuatoriana', 'VALIDACION', 'MANDATORY',

'IF se ingresa una cédula al crear o editar un trabajador',

'THEN el sistema valida: (a) longitud exacta de 10 dígitos, (b) solo caracteres numéricos, (c) dígito verificador válido según algoritmo oficial ecuatoriano.',

'ELSE si cualquier validación falla, el sistema muestra "Formato de cédula inválido. Debe ser 10 dígitos numéricos con dígito verificador correcto".',

'RF-03 Criterios de Aceptación', 'RF-03', 'CU-03', 'workers', NULL, 'COMBINED', 'COMBINED'),

('BR-013', 'Cédula única dentro del tenant', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se intenta registrar un trabajador con una cédula dentro de un tenant',

'THEN el sistema verifica unicidad compuesta (tenant_id + cedula) mediante UNIQUE constraint. Si es única, permite el registro.',

'ELSE el sistema rechaza con "Ya existe un trabajador con esta cédula en su empresa".',

'RF-03 Restricciones', 'RF-03', 'CU-03', 'workers', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-014', 'Trabajadores no poseen cuenta de usuario', 'NEGOCIO', 'MANDATORY',

'IF se registra un trabajador en el sistema',

'THEN el trabajador es solo un registro de datos en la tabla workers. NO se crea ningún registro en la tabla users ni se generan credenciales de acceso.',

'ELSE la clase Trabajador es disjunta con Usuario según la ontología OWL (owl:disjointWith).',

'RF-03 Restricciones', 'RF-03', 'CU-03', 'workers', 'users', 'APP_LOGIC', 'BACKEND'),

('BR-015', 'Visibilidad de trabajadores exclusiva del tenant', 'AISLAMIENTO', 'MANDATORY',

'IF un usuario tipo Cliente consulta la lista de trabajadores',

'THEN el sistema aplica RLS automáticamente: solo muestra trabajadores WHERE tenant_id = tenant del usuario autenticado.',

'ELSE si otro tenant intenta acceder por API al worker_id de otro tenant, retorna HTTP 404 (no 403, para no revelar existencia).',

'RF-03 Restricciones', 'RF-03', 'CU-03', 'workers', NULL, 'RLS_POLICY', 'DATABASE'),

('BR-016', 'Cédula inmutable tras creación', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF un Cliente intenta editar los datos de un trabajador existente',

'THEN el sistema permite modificar nombres, apellidos, email, teléfono y status. El campo cédula es de solo lectura y no puede modificarse.',

'ELSE si se intenta cambiar la cédula por API, el sistema ignora el campo o retorna error de validación.',

'CU-03 FA-01', 'RF-03', 'CU-03', 'workers', NULL, 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 5. INSERCIÓN DE REGLAS — SOLICITUD DE ACCESO (RF-04 / CU-04)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-017', 'Solo áreas autorizadas para el tenant', 'VALIDACION', 'MANDATORY',

'IF un Cliente selecciona áreas al crear una solicitud de acceso',

'THEN el sistema filtra el selector de áreas mostrando solo aquellas registradas en tenant_area_access para el tenant del usuario y el DC seleccionado, con revoked_at IS NULL.',

'ELSE si se fuerza un area_id no autorizado por API, el sistema retorna HTTP 403 "No tiene acceso a las áreas seleccionadas".',

'RF-04 Criterios de Aceptación', 'RF-04', 'CU-04', 'access_request_areas', 'tenant_area_access, areas', 'APP_LOGIC', 'COMBINED'),

('BR-018', 'Horario debe ser futuro al crear solicitud', 'VALIDACION', 'MANDATORY',

'IF se crea una solicitud de acceso con horario_inicio y horario_fin',

'THEN el sistema valida que AMBAS fechas sean estrictamente posteriores al momento actual (NOW()). Si son futuras, permite la creación.',

'ELSE el sistema rechaza con "Las fechas de horario deben ser posteriores al momento actual".',

'RF-04 Criterios de Aceptación', 'RF-04', 'CU-04', 'access_requests', NULL, 'COMBINED', 'COMBINED'),

('BR-019', 'Horario fin posterior a horario inicio', 'VALIDACION', 'MANDATORY',

'IF se definen horario_inicio y horario_fin en una solicitud',

'THEN el sistema valida que horario_fin \> horario_inicio (CHECK constraint en access_requests).',

'ELSE el sistema rechaza con "La fecha/hora de fin debe ser posterior a la de inicio".',

'RF-04 / Esquema BD', 'RF-04', 'CU-04', 'access_requests', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-020', 'Solicitud inmodificable tras aprobación', 'TRANSICION_ESTADO', 'MANDATORY',

'IF una solicitud tiene status = APROBADA y alguien intenta modificar sus campos',

'THEN el sistema bloquea cualquier UPDATE a campos de la solicitud (trabajo, herramientas, áreas, horario). Solo se permite actualizar campos de workflow (status, aprobado_por, etc.).',

'ELSE si la solicitud está en PENDIENTE, todos los campos son editables por el Cliente que la creó.',

'RF-04 Criterios de Aceptación', 'RF-04', 'CU-04', 'access_requests', NULL, 'TRIGGER', 'DATABASE'),

('BR-021', 'Solicitud se crea siempre en estado PENDIENTE', 'TRANSICION_ESTADO', 'MANDATORY',

'IF un Cliente crea una nueva solicitud de acceso',

'THEN el sistema asigna automáticamente status = PENDIENTE, independientemente de cualquier valor enviado. El campo status tiene DEFAULT ''PENDIENTE''.',

NULL,

'RF-04 / CU-04 RN-05', 'RF-04', 'CU-04', 'access_requests', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-022', 'Tenant inactivo no puede crear solicitudes', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un usuario perteneciente a un tenant intenta crear cualquier solicitud o trabajador',

'THEN el sistema verifica que el tenant del usuario tenga status = ACTIVO. Si está activo, permite la operación.',

'ELSE si el tenant está INACTIVO, el sistema bloquea toda operación y redirige a pantalla informativa "Su empresa se encuentra temporalmente deshabilitada".',

'CU-04 EX-06 / CU-03 EX-03', 'RF-04', 'CU-04', 'tenants', 'access_requests, workers', 'GUARD', 'BACKEND'),

('BR-023', 'DC inactivo no aparece en selectores', 'VALIDACION', 'MANDATORY',

'IF un Cliente accede al formulario de creación de solicitud',

'THEN el selector de Data Centers solo muestra DCs con status = ACTIVO que tengan áreas habilitadas para el tenant del usuario.',

'ELSE si se fuerza un datacenter_id inactivo por API, el sistema retorna error "Data Center no disponible".',

'CU-04 EX-05', 'RF-04', 'CU-04', 'data_centers', 'tenant_area_access', 'APP_LOGIC', 'COMBINED'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 6. INSERCIÓN DE REGLAS — APROBACIÓN (RF-05 / CU-05)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-024', 'Solo Admin DC del DC destino puede aprobar/denegar', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un Administrador de Data Center intenta aprobar o denegar una solicitud',

'THEN el sistema verifica que el datacenter_id de la solicitud coincida con el scope_id (datacenter_id) del rol ADMIN_DATACENTER del usuario.',

'ELSE si no coincide, el sistema retorna HTTP 403 "No tiene permisos para gestionar solicitudes de este Data Center".',

'RF-05 / CU-05 RN-01', 'RF-05', 'CU-05', 'access_requests', 'users, user_roles', 'GUARD', 'BACKEND'),

('BR-025', 'Denegación requiere motivo obligatorio', 'VALIDACION', 'MANDATORY',

'IF el Admin DC deniega una solicitud (status cambia a DENEGADA)',

'THEN el sistema verifica que el campo motivo_denegacion NO sea NULL ni vacío. CHECK constraint: CASE WHEN status=''DENEGADA'' THEN motivo_denegacion IS NOT NULL END.',

'ELSE si no proporciona motivo, el sistema bloquea la acción con "Debe ingresar un motivo de denegación".',

'RF-05 / CU-05 RN-02', 'RF-05', 'CU-05', 'access_requests', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-026', 'Comentario del aprobador es obligatorio siempre', 'VALIDACION', 'MANDATORY',

'IF el Admin DC aprueba o deniega una solicitud',

'THEN el sistema exige que el campo comentario_aprobador NO sea vacío, tanto para aprobación como para denegación.',

'ELSE si no ingresa comentario, el sistema bloquea la acción con "El comentario es obligatorio".',

'RF-05 / CU-05 RN-03', 'RF-05', 'CU-05', 'access_requests', NULL, 'APP_LOGIC', 'BACKEND'),

('BR-027', 'Registro obligatorio de datos del aprobador', 'AUDITORIA', 'MANDATORY',

'IF una solicitud es aprobada o denegada',

'THEN el sistema registra automáticamente: aprobado_por = user_id del Admin DC, aprobado_en = NOW(), comentario_aprobador = texto ingresado.',

NULL,

'RF-05 Registro obligatorio', 'RF-05', 'CU-05', 'access_requests', 'users', 'APP_LOGIC', 'BACKEND'),

('BR-028', 'Aprobación dispara generación automática de QR', 'WORKFLOW', 'MANDATORY',

'IF una solicitud cambia a estado APROBADA exitosamente',

'THEN el sistema dispara automáticamente el proceso de generación de QR firmado (CU-06): genera token RS256, crea hash, genera imagen QR y notifica al Cliente.',

'ELSE si la generación de QR falla, la solicitud permanece APROBADA pero se registra flag error_qr para reintento.',

'RF-05 / CU-05 RN-05 / CU-06', 'RF-05', 'CU-05', 'qr_tokens', 'access_requests', 'APP_LOGIC', 'BACKEND'),

('BR-029', 'No aprobar solicitud con horario expirado', 'EXPIRACION', 'MANDATORY',

'IF el Admin DC intenta aprobar una solicitud cuyo horario_fin ya pasó (horario_fin \< NOW())',

'THEN el sistema impide la aprobación y cambia automáticamente la solicitud a status = EXPIRADA.',

'ELSE si el horario_fin aún es futuro, permite la aprobación normalmente.',

'CU-05 EX-03 / RN-06', 'RF-05', 'CU-05', 'access_requests', NULL, 'APP_LOGIC', 'BACKEND'),

('BR-030', 'Concurrencia en aprobación', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF dos Administradores DC intentan aprobar/denegar la misma solicitud simultáneamente',

'THEN el sistema aplica bloqueo optimista: el primer UPDATE exitoso cambia el status; el segundo detecta que el status ya no es PENDIENTE y muestra alerta "Esta solicitud ya fue procesada por otro administrador".',

NULL,

'CU-05 EX-01', 'RF-05', 'CU-05', 'access_requests', NULL, 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 7. INSERCIÓN DE REGLAS — GENERACIÓN DE QR (RF-06 / CU-06)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-031', 'QR firmado criptográficamente con RS256', 'SEGURIDAD', 'MANDATORY',

'IF el sistema genera un token QR para una solicitud aprobada',

'THEN el payload (request_id, worker_id, datacenter_id, areas, horarios) se firma con clave privada RS256. Se almacena SOLO el hash SHA-256 del token (token_hash), NUNCA el token en texto plano.',

NULL,

'RF-06 / CU-06 RN-01/RN-02/RN-06', 'RF-06', 'CU-06', 'qr_tokens', 'access_requests', 'APP_LOGIC', 'BACKEND'),

('BR-032', 'QR válido solo dentro del horario aprobado', 'EXPIRACION', 'MANDATORY',

'IF un Agente escanea un QR cuyo horario actual NO está dentro del rango \[horario_inicio, horario_fin\] de la solicitud',

'THEN el sistema devuelve resultado = FUERA_HORARIO con pantalla roja y mensaje "Fuera del horario autorizado (HH:MM – HH:MM)".',

'ELSE si el horario actual está dentro del rango, continúa con las demás validaciones.',

'RF-06 Validaciones / CU-07', 'RF-06', 'CU-07', 'access_scan_events', 'qr_tokens, access_requests', 'APP_LOGIC', 'BACKEND'),

('BR-033', 'QR válido para un único ingreso', 'SEGURIDAD', 'MANDATORY',

'IF un QR es escaneado exitosamente (todas las validaciones pasan)',

'THEN el sistema marca inmediatamente el token: usado = true, usado_en = NOW(). Este cambio es IRREVERSIBLE (trigger impide revertir usado de true a false).',

'ELSE si el QR ya fue usado (usado = true), devuelve resultado = YA_UTILIZADO con pantalla roja.',

'RF-06 Validaciones / CU-06 RN-05', 'RF-06', 'CU-06', 'qr_tokens', NULL, 'TRIGGER', 'DATABASE'),

('BR-034', 'Expiración del token coincide con horario_fin', 'EXPIRACION', 'MANDATORY',

'IF se genera un QR token para una solicitud aprobada',

'THEN el campo expira_en se establece igual al horario_fin de la solicitud asociada.',

NULL,

'CU-06 RN-03', 'RF-06', 'CU-06', 'qr_tokens', 'access_requests', 'APP_LOGIC', 'BACKEND'),

('BR-035', 'No generar QR duplicado', 'INTEGRIDAD_DATOS', 'MANDATORY',

'IF se intenta generar un QR para una solicitud que ya tiene un QR válido (no invalidated)',

'THEN el sistema rechaza la generación duplicada (UNIQUE constraint en qr_tokens.request_id).',

'ELSE para regenerar, primero debe invalidarse el anterior (invalidated = true) y luego crear uno nuevo.',

'CU-06 EX-02', 'RF-06', 'CU-06', 'qr_tokens', NULL, 'CHECK_CONSTRAINT', 'DATABASE'),

('BR-036', 'No generar QR si horario ya expiró', 'EXPIRACION', 'MANDATORY',

'IF la solicitud aprobada tiene horario_fin \< NOW() al momento de generar el QR',

'THEN el sistema NO genera el QR y cambia la solicitud a status = EXPIRADA automáticamente.',

NULL,

'CU-06 EX-03', 'RF-06', 'CU-06', 'qr_tokens', 'access_requests', 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 8. INSERCIÓN DE REGLAS — ESCANEO QR (RF-07 / CU-07)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-037', 'Validación de firma criptográfica', 'SEGURIDAD', 'MANDATORY',

'IF un Agente escanea un código QR',

'THEN el sistema extrae el token y verifica la firma criptográfica usando la clave pública RS256. Si la firma es válida, continúa con las demás validaciones.',

'ELSE si la firma NO es válida, devuelve resultado = FIRMA_INVALIDA con pantalla roja y mensaje "QR inválido: firma no verificada". Registra el intento.',

'RF-07 / CU-07 Flujo Básico paso 4', 'RF-07', 'CU-07', 'access_scan_events', 'qr_tokens', 'APP_LOGIC', 'BACKEND'),

('BR-038', 'Validación de token no expirado', 'EXPIRACION', 'MANDATORY',

'IF el token del QR tiene expira_en \<= NOW()',

'THEN el sistema devuelve resultado = EXPIRADO con pantalla roja y mensaje "Acceso expirado". Registra el intento fallido.',

'ELSE si expira_en \> NOW(), continúa con la siguiente validación.',

'RF-06 Validaciones / CU-07', 'RF-07', 'CU-07', 'access_scan_events', 'qr_tokens', 'APP_LOGIC', 'BACKEND'),

('BR-039', 'Validación de token no utilizado', 'SEGURIDAD', 'MANDATORY',

'IF el token del QR tiene usado = true',

'THEN el sistema devuelve resultado = YA_UTILIZADO con pantalla roja y mensaje "QR ya utilizado" mostrando la fecha/hora del uso anterior (usado_en). Registra el intento.',

'ELSE si usado = false, continúa con la siguiente validación.',

'RF-06 Validaciones / CU-07', 'RF-07', 'CU-07', 'access_scan_events', 'qr_tokens', 'APP_LOGIC', 'BACKEND'),

('BR-040', 'Validación de DC correcto', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF el datacenter_id contenido en el token NO coincide con el datacenter_id del Agente que escanea',

'THEN el sistema devuelve resultado = DC_INCORRECTO con pantalla roja y mensaje "Este QR no corresponde a este Data Center". Registra el intento.',

'ELSE si coincide, el acceso es VÁLIDO (pantalla verde).',

'CU-07 EX-05', 'RF-07', 'CU-07', 'access_scan_events', 'qr_tokens, users', 'APP_LOGIC', 'BACKEND'),

('BR-041', 'Falla en validación rechaza acceso', 'SEGURIDAD', 'MANDATORY',

'IF cualquiera de las validaciones del QR falla (firma, expiración, uso, horario, DC)',

'THEN el sistema RECHAZA el acceso, muestra pantalla roja con el motivo específico y registra un AccessScanEvent con el resultado correspondiente.',

'ELSE si TODAS las validaciones pasan, registra ingreso exitoso (resultado = VALIDO) y marca token como usado.',

'RF-07 Criterios de Aceptación', 'RF-07', 'CU-07', 'access_scan_events', 'qr_tokens, access_requests', 'APP_LOGIC', 'BACKEND'),

('BR-042', 'Ingreso exitoso marca solicitud como UTILIZADA', 'TRANSICION_ESTADO', 'MANDATORY',

'IF un escaneo QR es exitoso (resultado = VALIDO)',

'THEN el sistema cambia la solicitud asociada a status = UTILIZADA, marca el token como usado = true, usado_en = NOW(), y crea el AccessScanEvent.',

NULL,

'RF-07 / CU-07 RN-06', 'RF-07', 'CU-07', 'access_requests', 'qr_tokens, access_scan_events', 'APP_LOGIC', 'BACKEND'),

('BR-043', 'Registro de intentos exitosos y fallidos', 'AUDITORIA', 'MANDATORY',

'IF un Agente escanea un QR (independientemente del resultado)',

'THEN el sistema SIEMPRE crea un registro en access_scan_events con: agente_id, request_id, datacenter_id, fecha, resultado, observaciones.',

NULL,

'CU-07 RN-05', 'RF-07', 'CU-07', 'access_scan_events', NULL, 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 9. INSERCIÓN DE REGLAS — REPORTES (RF-08 / CU-08)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-044', 'Scope de visibilidad en reportes por rol', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF el Admin Plataforma consulta reportes',

'THEN ve reportes GLOBALES (todos los DC, todos los tenants).',

NULL,

'RF-08 / CU-08 RN-01', 'RF-08', 'CU-08', 'access_scan_events', 'access_requests', 'RLS_POLICY', 'DATABASE'),

('BR-045', 'Admin DC ve solo visitas de su DC', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un Admin DC consulta reportes de visitas',

'THEN el sistema filtra automáticamente WHERE datacenter_id = scope_id del Admin DC.',

'ELSE si intenta acceder a datos de otro DC, la política RLS oculta los registros.',

'CU-08 RN-02', 'RF-08', 'CU-08', 'access_scan_events', NULL, 'RLS_POLICY', 'DATABASE'),

('BR-046', 'Cliente ve solo visitas de sus trabajadores', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un Cliente Telconet consulta historial de visitas',

'THEN el sistema filtra por tenant_id del usuario, mostrando solo visitas de sus propios trabajadores.',

NULL,

'CU-08 RN-03', 'RF-08', 'CU-08', 'access_scan_events', 'access_requests, workers', 'RLS_POLICY', 'DATABASE'),

('BR-047', 'Exportación limitada a 10,000 registros', 'NEGOCIO', 'WARNING',

'IF un usuario solicita exportar un reporte con más de 10,000 registros',

'THEN el sistema limita la exportación a 10,000 registros o genera la exportación de forma asíncrona, notificando al usuario cuando esté lista.',

'ELSE si tiene ≤ 10,000 registros, la exportación es síncrona e inmediata.',

'CU-08 EX-02', 'RF-08', 'CU-08', 'report_export_logs', NULL, 'APP_LOGIC', 'BACKEND'),

('BR-048', 'Exportaciones con marca de agua', 'AUDITORIA', 'MANDATORY',

'IF un usuario exporta un reporte en cualquier formato (CSV, PDF, Excel)',

'THEN el sistema incluye marca de agua con: fecha de generación, nombre del usuario que exportó, y se registra en report_export_logs.',

NULL,

'CU-08 RN-06', 'RF-08', 'CU-08', 'report_export_logs', 'users', 'APP_LOGIC', 'BACKEND'),

-- ─────────────────────────────────────────────────────────────────────────────

-- 10. INSERCIÓN DE REGLAS — AUDITORÍA GLOBAL (RNF / Transversales)

-- ─────────────────────────────────────────────────────────────────────────────

('BR-049', 'Toda acción relevante genera registro de auditoría', 'AUDITORIA', 'MANDATORY',

'IF un usuario ejecuta cualquier acción relevante (CREATE, UPDATE, DELETE lógico, APPROVE, DENY, SCAN, EXPORT, etc.)',

'THEN el sistema genera un registro inmutable en audit_logs con: actor_id, actor_rol, entidad, entidad_id, accion, estado_anterior (JSONB), estado_nuevo (JSONB), tenant_id, datacenter_id, ip_address, user_agent, timestamp.',

NULL,

'Sección 5 RNF Auditoría', NULL, NULL, 'audit_logs', 'users', 'APP_LOGIC', 'BACKEND'),

('BR-050', 'Logs de auditoría son inmutables', 'AUDITORIA', 'MANDATORY',

'IF alguien intenta ejecutar UPDATE o DELETE sobre la tabla audit_logs',

'THEN el trigger trg_audit_immutable lanza EXCEPTION "Los registros de auditoría son inmutables. No se permite UPDATE ni DELETE".',

NULL,

'Sección 5 RNF / Esquema BD', NULL, NULL, 'audit_logs', NULL, 'TRIGGER', 'DATABASE'),

('BR-051', 'Eliminación lógica obligatoria en todas las entidades', 'NEGOCIO', 'MANDATORY',

'IF alguien intenta eliminar físicamente (DELETE) un registro de tenants, data_centers, areas, workers, users o access_requests',

'THEN el sistema prohíbe la eliminación física. Solo se permite desactivación lógica (UPDATE status = INACTIVO). Los FK con ON DELETE RESTRICT previenen borrado accidental.',

NULL,

'Ontología OWL Axioma: Eliminación Lógica', NULL, NULL, 'tenants', 'data_centers, areas, workers, users, access_requests', 'APP_LOGIC', 'COMBINED'),

('BR-052', 'Expiración automática de solicitudes vencidas', 'EXPIRACION', 'MANDATORY',

'IF una solicitud tiene status IN (PENDIENTE, APROBADA) y su horario_fin \< NOW()',

'THEN un CRON job (scheduler) ejecuta periódicamente: UPDATE access_requests SET status = ''EXPIRADA'', updated_at = NOW() WHERE status IN (''PENDIENTE'',''APROBADA'') AND horario_fin \< NOW().',

NULL,

'CU-04 RN-07 / Esquema BD', 'RF-04', 'CU-04', 'access_requests', NULL, 'CRON_JOB', 'BACKEND'),

('BR-053', 'HTTPS obligatorio en toda comunicación', 'SEGURIDAD', 'MANDATORY',

'IF cualquier cliente (frontend, API, móvil) intenta comunicarse con el sistema',

'THEN toda comunicación debe ser sobre HTTPS (TLS 1.2+). El API Gateway rechaza conexiones HTTP con redirect 301 a HTTPS.',

NULL,

'Sección 5 RNF Seguridad', NULL, NULL, 'N/A (infraestructura)', NULL, 'MIDDLEWARE', 'GATEWAY'),

('BR-054', 'JWT firmado con RS256', 'SEGURIDAD', 'MANDATORY',

'IF un usuario se autentica exitosamente en el sistema',

'THEN el sistema emite un JWT firmado con algoritmo RS256 (asimétrico) que incluye: user_id, tenant_id, datacenter_id, roles, scope, exp. El JWT se valida con clave pública en cada request.',

'ELSE si el JWT es inválido, expirado o con firma incorrecta, el API Gateway retorna HTTP 401 Unauthorized.',

'Sección 5 RNF Seguridad', NULL, NULL, 'users', 'user_roles', 'MIDDLEWARE', 'GATEWAY'),

('BR-055', 'Menú dinámico según permisos del rol', 'RESTRICCION_ACCESO', 'MANDATORY',

'IF un usuario inicia sesión en el frontend',

'THEN el sistema construye el menú lateral dinámicamente consultando los permisos asociados al rol del usuario. Solo se muestran módulos para los cuales tiene permiso.',

'ELSE los módulos sin permiso no se renderizan en el DOM (no solo se ocultan con CSS).',

'Sección 9.1 Principios de Diseño', NULL, NULL, 'permissions', 'user_roles, role_permissions', 'FRONTEND_VALIDATION', 'FRONTEND'),

('BR-056', 'Confirmaciones obligatorias para acciones críticas', 'NEGOCIO', 'MANDATORY',

'IF un usuario ejecuta una acción crítica (aprobar, denegar, desactivar tenant/DC/área/trabajador, revocar acceso)',

'THEN el frontend muestra un diálogo de confirmación obligatorio con descripción de la acción y sus consecuencias. Solo procede si el usuario confirma explícitamente.',

'ELSE si el usuario cancela, la acción no se ejecuta y se permanece en la pantalla actual.',

'Sección 11 UX Empresarial', NULL, NULL, 'N/A (frontend)', NULL, 'FRONTEND_VALIDATION', 'FRONTEND'),

('BR-057', 'Validación QR en menos de 500ms', 'NEGOCIO', 'MANDATORY',

'IF un Agente escanea un QR y el sistema inicia la validación',

'THEN todo el proceso de validación (firma, expiración, uso, horario, DC) debe completarse en menos de 500 milisegundos. Índice UNIQUE en qr_tokens.token_hash garantiza búsqueda O(1).',

'ELSE si el tiempo excede 500ms, se registra una alerta de rendimiento en los logs de observabilidad.',

'Sección 5 RNF Rendimiento', NULL, 'CU-07', 'qr_tokens', 'access_scan_events', 'APP_LOGIC', 'BACKEND'),

('BR-058', 'Solicitudes redirigidas tras remoción de áreas de tenant', 'WORKFLOW', 'WARNING',

'IF el Administrador de Plataforma remueve áreas habilitadas de un tenant (revoca tenant_area_access)',

'THEN el sistema notifica al Administrador DC sobre solicitudes PENDIENTES que incluyan las áreas removidas.',

'ELSE las solicitudes ya APROBADAS no se afectan retroactivamente.',

'CU-01 FA-04', 'RF-01', 'CU-01', 'tenant_area_access', 'access_requests, access_request_areas', 'APP_LOGIC', 'BACKEND'),

('BR-059', 'Token QR irreversible (usado = true)', 'SEGURIDAD', 'MANDATORY',

'IF se intenta ejecutar UPDATE en qr_tokens cambiando usado de true a false',

'THEN el trigger trg_qr_irreversible lanza EXCEPTION "El estado usado=true de un QR Token es irreversible".',

NULL,

'Ontología OWL Axioma: Token QR de Uso Único / Esquema BD', 'RF-06', 'CU-06', 'qr_tokens', NULL, 'TRIGGER', 'DATABASE'),

('BR-060', 'Valores válidos de resultado de escaneo', 'VALIDACION', 'MANDATORY',

'IF se registra un AccessScanEvent',

'THEN el campo resultado solo acepta valores del enum: VALIDO, EXPIRADO, YA_UTILIZADO, FUERA_HORARIO, FIRMA_INVALIDA, DC_INCORRECTO. CHECK constraint en access_scan_events.resultado.',

'ELSE cualquier otro valor es rechazado por la base de datos.',

'Ontología OWL: ResultadoEscaneo / Esquema BD', 'RF-07', 'CU-07', 'access_scan_events', NULL, 'CHECK_CONSTRAINT', 'DATABASE');

-- ─────────────────────────────────────────────────────────────────────────────

-- 3. VISTA RESUMEN POR CATEGORÍA

-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_business_rules_summary AS

SELECT

category,

COUNT(\*) AS total_rules,

COUNT(\*) FILTER (WHERE severity = 'MANDATORY') AS mandatory,

COUNT(\*) FILTER (WHERE severity = 'WARNING') AS warning,

COUNT(\*) FILTER (WHERE implementation_layer = 'DATABASE') AS db_layer,

COUNT(\*) FILTER (WHERE implementation_layer = 'BACKEND') AS backend_layer,

COUNT(\*) FILTER (WHERE implementation_layer = 'FRONTEND') AS frontend_layer,

COUNT(\*) FILTER (WHERE implementation_layer = 'GATEWAY') AS gateway_layer,

COUNT(\*) FILTER (WHERE implementation_layer = 'COMBINED') AS combined_layer

FROM business_rules

WHERE is_active = true

GROUP BY category

ORDER BY total_rules DESC;

-- ─────────────────────────────────────────────────────────────────────────────

-- 4. VISTA DE TRAZABILIDAD: Regla → Requerimiento → Caso de Uso

-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_business_rules_traceability AS

SELECT

rule_code,

rule_name,

category,

severity,

source_requirement,

source_use_case,

entity_affected,

implementation_type,

implementation_layer,

LEFT(condition_if, 80) \|\| '...' AS condition_preview

FROM business_rules

WHERE is_active = true

ORDER BY rule_code;

-- ═══════════════════════════════════════════════════════════════════════════════

-- FIN — 60 reglas de negocio IF-THEN extraídas y catalogadas

-- ═══════════════════════════════════════════════════════════════════════════════
