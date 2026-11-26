from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: str
    # Separador de argumentos al mostrar fórmulas de Excel: «;» en Argentina, «,» en México.
    formula_separador_argumentos: str = ";"
    secret_key: str
    gobernanza_password: str
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    google_genai_use_enterprise: bool = False
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "global"
    google_application_credentials: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    ollama_api_key: Optional[str] = None
    renderix_api_key: Optional[str] = None
    modelos_suspendidos: str = ""  # Identificadores separados por coma; no modifica credenciales.
    # Lector del cuadro (services/lector_mapa.py): apagado | observar (lee y guarda, sin señales) | activo.
    lector_ia: str = "apagado"
    # Lectoras del lector del cuadro y de la interpretación previa, separadas por coma. DeepSeek no lee por defecto:
    # se agrega a mano (LECTOR_LECTORAS=gpt,gemini,deepseek) y entonces hay que volver a declararlo en /privacidad.
    lector_lectoras: str = "gpt,gemini"
    renderix_model: str = "renderix-es:latest"
    renderix_base_url: str = "https://ia.plataformaialocal.com/local/v1"
    openai_model: str = "gpt-4.1-mini"
    # Verificación semántica de citas; configurable por separado del chat.
    openai_model_verificador_incubadora: str = "gpt-5.4-mini"
    anthropic_model: str = "claude-sonnet-4-6"
    gemini_model: str = "gemini-2.5-flash"
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://127.0.0.1:11434"
    monitoreo_proyecto_id: Optional[int] = None  # Piloto habilitado expresamente por el responsable.
    # 0.10.85: proyectos de seguimiento propio de las herramientas (ids separados por coma): Monitoreo registra su
    # avance, riesgos, decisiones e indicadores, sin que cuenten como el piloto ni como proyecto ganador.
    monitoreo_proyectos_propios: str = ""
    # 0.10.72: grupos de cursada cuyos proyectos usan Monitoreo en modo prueba, con su prototipo (separados por coma).
    monitoreo_grupos_prueba: str = "Grupo A · comisión 2,Grupo B"  # 0.10.80: también Grupo B
    # 0.10.80: grupos de cursada sin votación: no ven la actividad ni la votación de la galería, y el servidor no
    # acepta votos (Maxi, 08/11/2026: en la comisión 2 y la primera del grupo B se implementan todos los proyectos).
    grupos_sin_votacion: str = "Grupo A · comisión 2,Grupo B"
    incubadora_ambito: str = "publico"  # «organizacion» adapta la tutora de la Incubadora a empresas, cooperativas y ONG.
    limite_analisis_ia_dia: int = 20  # Análisis (y exploraciones) con IA por usuario en 24 h; 0 = sin tope.
    limite_mensajes_incubadora_dia: int = 150  # Mensajes a la IA de la Incubadora por usuario en 24 h; 0 = sin tope.
    incubadora_max_integrantes: int = 5  # Personas por proyecto en equipo de la Incubadora, contando a quien lo abrió (0.10.67).
    alertas_email: str = ""  # Destinatario fijo de scripts/alerta_errores.py; si falta, el primer admin con correo.
    docente_aviso_email: str = ""  # Correos (separados por coma) que reciben el aviso de cada consulta al docente de la Incubadora.
    usuarios_excluidos_metricas: str = ""  # Correos separados por coma: cuentas de prueba fuera de las métricas.
    app_port: int = 6163
    admin_email: str = "admin@gobernanza.local"
    admin_name: str = "Administrador"
    admin_password: Optional[str] = None
    public_base_url: str = "https://gov4action.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_tls: bool = True
    smtp_ssl: bool = False

    @field_validator("secret_key", "gobernanza_password", "admin_password")
    @classmethod
    def validar_credenciales(cls, value, info):
        if value is None and info.field_name == "admin_password":
            return value
        minimo = 32 if info.field_name == "secret_key" else 12
        ejemplos = {"cambiar", "changeme", "change-me", "change_me", "secret", "password"}
        if not value or value.strip().lower() in ejemplos or len(value.strip()) < minimo:
            raise ValueError(f"{info.field_name.upper()} debe reemplazarse por un valor propio de al menos {minimo} caracteres")
        return value

    def modelo_habilitado(self, modelo: str) -> bool:
        return modelo not in {m.strip().lower() for m in self.modelos_suspendidos.split(",") if m.strip()}


settings = Settings()  # type: ignore[call-arg]
