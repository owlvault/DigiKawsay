"""
Simulación de Piloto ACME - Fábrica de Tornillos B2B
100 participantes en 5 áreas
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración del piloto
TENANT_NAME = "ACME Tornillos S.A.S"
AREAS = {
    "mercadeo": {"count": 20, "positions": ["Director de Mercadeo", "Analista de Marketing Digital", "Community Manager", "Diseñador Gráfico", "Especialista SEO/SEM"]},
    "comercial": {"count": 25, "positions": ["Director Comercial", "Ejecutivo de Ventas", "Key Account Manager", "Asesor Comercial", "Coordinador de Ventas"]},
    "direccion_financiera": {"count": 15, "positions": ["Director Financiero", "Contador", "Analista Financiero", "Tesorero", "Auxiliar Contable"]},
    "produccion": {"count": 25, "positions": ["Director de Producción", "Ingeniero de Procesos", "Supervisor de Planta", "Operario Especializado", "Control de Calidad"]},
    "tecnologia": {"count": 15, "positions": ["Director de TI", "Desarrollador Full Stack", "Administrador de Sistemas", "Analista de Datos", "Soporte Técnico"]}
}

# Nombres colombianos para la simulación
NOMBRES = ["Carlos", "María", "Juan", "Ana", "Pedro", "Laura", "Diego", "Sofía", "Andrés", "Valentina", 
           "Miguel", "Camila", "David", "Isabella", "Santiago", "Daniela", "Alejandro", "Paula", "Sebastián", "Natalia",
           "Felipe", "Gabriela", "Nicolás", "Mariana", "Julián", "Carolina", "Mateo", "Andrea", "Daniel", "Luisa"]
APELLIDOS = ["García", "Rodríguez", "Martínez", "López", "González", "Hernández", "Pérez", "Sánchez", "Ramírez", "Torres",
             "Flores", "Rivera", "Gómez", "Díaz", "Reyes", "Morales", "Cruz", "Ortiz", "Gutiérrez", "Chávez",
             "Vargas", "Castro", "Romero", "Jiménez", "Ruiz", "Mendoza", "Medina", "Aguilar", "Moreno", "Herrera"]

# Campañas para el piloto
CAMPAIGNS = [
    {
        "name": "Diagnóstico Clima Organizacional 2025",
        "description": "Evaluación integral del ambiente laboral en ACME para identificar oportunidades de mejora en bienestar y productividad.",
        "objectives": ["Medir satisfacción laboral", "Identificar factores de estrés", "Evaluar comunicación interna", "Detectar necesidades de capacitación"]
    },
    {
        "name": "Transformación Digital B2B",
        "description": "Explorar la experiencia de los colaboradores con la plataforma de e-commerce y procesos digitales en la venta a ferreterías.",
        "objectives": ["Evaluar usabilidad de la plataforma", "Identificar cuellos de botella", "Recoger ideas de mejora", "Medir adopción digital"]
    },
    {
        "name": "Innovación en Productos",
        "description": "Recopilar insights sobre nuevas líneas de tornillería y soluciones para el mercado ferretero colombiano.",
        "objectives": ["Identificar tendencias del mercado", "Recoger ideas de productos", "Evaluar competitividad", "Explorar nuevos nichos"]
    },
    {
        "name": "Cultura de Seguridad Industrial",
        "description": "Investigación participativa sobre prácticas de seguridad en planta y prevención de accidentes.",
        "objectives": ["Evaluar cultura de seguridad", "Identificar riesgos", "Medir cumplimiento de protocolos", "Recoger mejores prácticas"]
    }
]

# Scripts de conversación para VAL
SCRIPT_SEGMENTS = {
    "clima": [
        {"type": "greeting", "content": "¡Hola! Soy VAL, tu facilitador de conversación. Hoy quiero conocer tu experiencia trabajando en ACME. ¿Cómo te sientes en tu día a día laboral?"},
        {"type": "exploration", "content": "Cuéntame más sobre tu relación con tu equipo de trabajo. ¿Cómo describirías la comunicación con tus compañeros y líderes?"},
        {"type": "deep_dive", "content": "¿Qué aspectos de tu trabajo te generan más satisfacción? ¿Y cuáles te gustaría que mejoraran?"},
        {"type": "closing", "content": "Gracias por compartir tu perspectiva. Tu voz es importante para construir una mejor ACME. ¿Hay algo más que quieras agregar?"}
    ],
    "digital": [
        {"type": "greeting", "content": "¡Hola! Soy VAL. Hoy conversaremos sobre tu experiencia con las herramientas digitales de ACME. ¿Cómo ha sido tu interacción con la plataforma de ventas B2B?"},
        {"type": "exploration", "content": "¿Qué funcionalidades de la plataforma usas más frecuentemente? ¿Encuentras alguna dificultad en el proceso?"},
        {"type": "deep_dive", "content": "Si pudieras mejorar algo de nuestra plataforma digital para las ferreterías, ¿qué sería?"},
        {"type": "closing", "content": "Excelente retroalimentación. Tu experiencia nos ayuda a mejorar. ¿Alguna idea adicional para la transformación digital?"}
    ],
    "innovacion": [
        {"type": "greeting", "content": "¡Hola! Soy VAL. Quiero explorar contigo ideas para innovar en ACME. ¿Qué tendencias ves en el mercado de tornillería y ferretería?"},
        {"type": "exploration", "content": "Desde tu área, ¿qué oportunidades identificas para nuevos productos o servicios?"},
        {"type": "deep_dive", "content": "¿Qué necesidades de las ferreterías colombianas crees que no estamos atendiendo actualmente?"},
        {"type": "closing", "content": "Gracias por tus ideas. La innovación nace de conversaciones como esta. ¿Algo más que quieras proponer?"}
    ],
    "seguridad": [
        {"type": "greeting", "content": "¡Hola! Soy VAL. Hoy hablaremos sobre seguridad industrial en ACME. ¿Cómo percibes la cultura de seguridad en tu área de trabajo?"},
        {"type": "exploration", "content": "¿Qué protocolos de seguridad consideras más importantes? ¿Se cumplen consistentemente?"},
        {"type": "deep_dive", "content": "¿Has identificado algún riesgo o situación que podría mejorarse para prevenir accidentes?"},
        {"type": "closing", "content": "Tu perspectiva es valiosa para un ambiente seguro. ¿Tienes alguna sugerencia adicional de seguridad?"}
    ]
}

# Respuestas simuladas de participantes
PARTICIPANT_RESPONSES = {
    "clima": {
        "mercadeo": [
            "Me siento bien, aunque a veces la carga de trabajo es intensa con las campañas digitales.",
            "La comunicación con el equipo es buena, pero a veces falta alineación con comercial.",
            "Me gusta la creatividad del trabajo, pero quisiera más herramientas de análisis.",
            "Siento que mis ideas son escuchadas, aunque los procesos de aprobación son lentos."
        ],
        "comercial": [
            "El ritmo es fuerte, las metas son exigentes pero alcanzables.",
            "Necesitamos mejor coordinación con producción para los tiempos de entrega.",
            "Las ferreterías valoran nuestro servicio, pero piden más variedad de productos.",
            "Me gustaría más capacitación en ventas consultivas B2B."
        ],
        "direccion_financiera": [
            "El ambiente es profesional, aunque hay presión por los cierres mensuales.",
            "La comunicación con otras áreas podría mejorar en temas de presupuesto.",
            "Necesitamos mejor integración de los sistemas financieros.",
            "Me preocupa la rotación de cartera con algunas ferreterías."
        ],
        "produccion": [
            "El trabajo en planta es demandante pero gratificante.",
            "Los turnos rotativos afectan un poco la vida familiar.",
            "La maquinaria necesita actualización para mejorar productividad.",
            "El equipo de producción es muy unido y colaborativo."
        ],
        "tecnologia": [
            "Estamos en plena transformación digital, hay mucho por hacer.",
            "La plataforma B2B necesita mejoras de rendimiento.",
            "Falta personal para atender todos los requerimientos.",
            "Me gusta el reto tecnológico pero necesitamos más recursos."
        ]
    },
    "digital": {
        "mercadeo": [
            "La plataforma web es funcional pero el diseño podría ser más moderno.",
            "Necesitamos mejor integración con redes sociales y CRM.",
            "Los reportes de analytics son limitados.",
            "Las ferreterías piden una app móvil para hacer pedidos."
        ],
        "comercial": [
            "El portal B2B funciona bien para pedidos básicos.",
            "Falta un configurador de productos más intuitivo.",
            "Los clientes piden ver disponibilidad de inventario en tiempo real.",
            "El proceso de cotización debería ser más ágil."
        ],
        "direccion_financiera": [
            "La facturación electrónica funciona bien con la DIAN.",
            "Necesitamos mejor trazabilidad de pagos en la plataforma.",
            "Los reportes financieros podrían automatizarse más.",
            "La integración con el banco podría mejorarse."
        ],
        "produccion": [
            "El sistema de producción está desconectado del e-commerce.",
            "Necesitamos visibilidad de pedidos en tiempo real.",
            "La trazabilidad de lotes es manual aún.",
            "Un dashboard de producción sería muy útil."
        ],
        "tecnologia": [
            "La arquitectura actual tiene limitaciones de escalabilidad.",
            "Estamos migrando a la nube pero el proceso es lento.",
            "La seguridad de la plataforma necesita reforzarse.",
            "APIs para integración con ERPs de ferreterías es prioritario."
        ]
    }
}

# Insights generados de las conversaciones
INSIGHTS_TEMPLATES = [
    {"category": "clima_laboral", "theme": "Carga de trabajo", "insight": "El 65% de los participantes de {area} mencionan alta carga laboral, especialmente en periodos de {contexto}."},
    {"category": "clima_laboral", "theme": "Comunicación", "insight": "Se identifica necesidad de mejor comunicación entre {area1} y {area2} para optimizar {proceso}."},
    {"category": "digital", "theme": "Plataforma B2B", "insight": "Las ferreterías solicitan funcionalidad de {feature} según el 78% de participantes de {area}."},
    {"category": "digital", "theme": "Automatización", "insight": "Oportunidad de automatizar {proceso} identificada por equipo de {area}."},
    {"category": "innovacion", "theme": "Nuevos productos", "insight": "Demanda detectada de tornillería especializada para {segmento} según análisis de {area}."},
    {"category": "innovacion", "theme": "Mercado", "insight": "Tendencia de {tendencia} identificada como oportunidad por el equipo comercial."},
    {"category": "seguridad", "theme": "Protocolos", "insight": "Área de {area} sugiere reforzar protocolo de {protocolo} para prevenir {riesgo}."},
    {"category": "seguridad", "theme": "Capacitación", "insight": "Necesidad de capacitación en {tema} para personal de {area}."}
]

async def create_tenant():
    """Crear el tenant ACME"""
    tenant_id = str(uuid.uuid4())
    tenant = {
        "id": tenant_id,
        "name": TENANT_NAME,
        "description": "Fábrica de tornillos líder en Colombia. Venta B2B a ferreterías a través de plataforma digital.",
        "logo_url": None,
        "is_active": True,
        "industry": "Manufactura - Tornillería",
        "country": "Colombia",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tenants.insert_one(tenant)
    print(f"✅ Tenant creado: {TENANT_NAME} (ID: {tenant_id})")
    return tenant_id

async def create_users(tenant_id):
    """Crear 100 usuarios en 5 áreas"""
    users = []
    user_count = 0
    
    for area, config in AREAS.items():
        for i in range(config["count"]):
            user_count += 1
            nombre = random.choice(NOMBRES)
            apellido = random.choice(APELLIDOS)
            position = random.choice(config["positions"])
            
            user_id = str(uuid.uuid4())
            email = f"{nombre.lower()}.{apellido.lower()}{user_count}@acme.com.co"
            
            user = {
                "id": user_id,
                "email": email,
                "full_name": f"{nombre} {apellido}",
                "hashed_password": pwd_context.hash("acme2025"),
                "role": "participant",
                "tenant_id": tenant_id,
                "department": area.replace("_", " ").title(),
                "position": position,
                "is_active": True,
                "pseudonym_id": f"P-{uuid.uuid4().hex[:8].upper()}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            users.append(user)
    
    # Crear admin y facilitador de ACME
    admin = {
        "id": str(uuid.uuid4()),
        "email": "admin@acme.com.co",
        "full_name": "Administrador ACME",
        "hashed_password": pwd_context.hash("acme2025"),
        "role": "admin",
        "tenant_id": tenant_id,
        "department": "Dirección General",
        "position": "Administrador del Sistema",
        "is_active": True,
        "pseudonym_id": f"P-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    users.append(admin)
    
    facilitator = {
        "id": str(uuid.uuid4()),
        "email": "facilitador@acme.com.co",
        "full_name": "Facilitador PAR",
        "hashed_password": pwd_context.hash("acme2025"),
        "role": "facilitator",
        "tenant_id": tenant_id,
        "department": "Gestión Humana",
        "position": "Facilitador de Investigación",
        "is_active": True,
        "pseudonym_id": f"P-{uuid.uuid4().hex[:8].upper()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    users.append(facilitator)
    
    await db.users.insert_many(users)
    print(f"✅ {len(users)} usuarios creados (100 participantes + admin + facilitador)")
    return users

async def create_campaigns(tenant_id):
    """Crear campañas para el piloto"""
    campaigns = []
    
    for i, camp_data in enumerate(CAMPAIGNS):
        campaign_id = str(uuid.uuid4())
        start_date = datetime.now(timezone.utc) - timedelta(days=random.randint(5, 15))
        
        campaign = {
            "id": campaign_id,
            "tenant_id": tenant_id,
            "name": camp_data["name"],
            "description": camp_data["description"],
            "objectives": camp_data["objectives"],
            "status": "active" if i < 2 else "draft",
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=30)).isoformat(),
            "target_participants": 100,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        campaigns.append(campaign)
    
    await db.campaigns.insert_many(campaigns)
    print(f"✅ {len(campaigns)} campañas creadas")
    return campaigns

async def create_scripts(campaigns):
    """Crear scripts de conversación para cada campaña"""
    scripts = []
    script_types = ["clima", "digital", "innovacion", "seguridad"]
    
    for i, campaign in enumerate(campaigns):
        script_type = script_types[i % len(script_types)]
        segments = SCRIPT_SEGMENTS[script_type]
        
        script = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign["id"],
            "tenant_id": campaign["tenant_id"],
            "name": f"Guión - {campaign['name']}",
            "version": 1,
            "is_active": True,
            "segments": segments,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        scripts.append(script)
    
    await db.scripts.insert_many(scripts)
    print(f"✅ {len(scripts)} scripts de conversación creados")
    return scripts

async def create_sessions_and_messages(campaigns, users, tenant_id):
    """Crear sesiones de chat simuladas"""
    sessions = []
    messages_to_insert = []
    
    participants = [u for u in users if u["role"] == "participant"]
    active_campaigns = [c for c in campaigns if c["status"] == "active"]
    
    for campaign in active_campaigns:
        # 60-80% de participación
        participating_users = random.sample(participants, int(len(participants) * random.uniform(0.6, 0.8)))
        
        for user in participating_users:
            session_id = str(uuid.uuid4())
            area_key = user["department"].lower().replace(" ", "_")
            
            # Determinar si la sesión está completa
            is_complete = random.random() > 0.2  # 80% completas
            status = "completed" if is_complete else random.choice(["in_progress", "abandoned"])
            
            session = {
                "id": session_id,
                "campaign_id": campaign["id"],
                "tenant_id": tenant_id,
                "participant_id": user["id"],
                "participant_pseudonym": user["pseudonym_id"],
                "status": status,
                "started_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat() if is_complete else None,
                "consent_given": True,
                "consent_timestamp": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            sessions.append(session)
            
            # Crear mensajes de la conversación
            script_type = "clima" if "Clima" in campaign["name"] else "digital" if "Digital" in campaign["name"] else "innovacion" if "Innovación" in campaign["name"] else "seguridad"
            
            if area_key in PARTICIPANT_RESPONSES.get(script_type, {}):
                responses = PARTICIPANT_RESPONSES[script_type][area_key]
            else:
                responses = PARTICIPANT_RESPONSES.get(script_type, {}).get("comercial", ["Gracias por la oportunidad de participar."])
            
            # Mensajes de VAL y respuestas del participante
            segments = SCRIPT_SEGMENTS[script_type]
            num_exchanges = len(segments) if is_complete else random.randint(1, len(segments)-1)
            
            for j in range(num_exchanges):
                # Mensaje de VAL
                val_msg = {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "role": "assistant",
                    "content": segments[j]["content"],
                    "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(10, 60))).isoformat()
                }
                messages_to_insert.append(val_msg)
                
                # Respuesta del participante
                participant_msg = {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "role": "user",
                    "content": random.choice(responses),
                    "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 30))).isoformat()
                }
                messages_to_insert.append(participant_msg)
    
    await db.sessions.insert_many(sessions)
    await db.messages.insert_many(messages_to_insert)
    print(f"✅ {len(sessions)} sesiones de chat creadas")
    print(f"✅ {len(messages_to_insert)} mensajes de conversación generados")
    return sessions

async def create_insights(campaigns, tenant_id):
    """Crear insights extraídos de las conversaciones"""
    insights = []
    areas = list(AREAS.keys())
    
    contextos = ["cierre de mes", "lanzamiento de campaña", "fin de año", "temporada alta"]
    features = ["inventario en tiempo real", "app móvil", "cotizador automático", "seguimiento de pedidos"]
    procesos = ["facturación", "despacho", "cotización", "atención al cliente"]
    segmentos = ["construcción", "automotriz", "muebles", "industrial pesado"]
    tendencias = ["sostenibilidad", "automatización", "e-commerce", "servicio personalizado"]
    protocolos = ["uso de EPP", "manejo de cargas", "operación de maquinaria", "emergencias"]
    riesgos = ["lesiones", "accidentes", "fatiga", "exposición a ruido"]
    temas_capacitacion = ["primeros auxilios", "manejo de extintores", "trabajo en alturas", "ergonomía"]
    
    for campaign in campaigns:
        num_insights = random.randint(8, 15)
        
        for _ in range(num_insights):
            template = random.choice(INSIGHTS_TEMPLATES)
            area1 = random.choice(areas).replace("_", " ").title()
            area2 = random.choice(areas).replace("_", " ").title()
            
            insight_text = template["insight"].format(
                area=area1,
                area1=area1,
                area2=area2,
                contexto=random.choice(contextos),
                feature=random.choice(features),
                proceso=random.choice(procesos),
                segmento=random.choice(segmentos),
                tendencia=random.choice(tendencias),
                protocolo=random.choice(protocolos),
                riesgo=random.choice(riesgos),
                tema=random.choice(temas_capacitacion)
            )
            
            insight = {
                "id": str(uuid.uuid4()),
                "campaign_id": campaign["id"],
                "tenant_id": tenant_id,
                "category": template["category"],
                "theme": template["theme"],
                "content": insight_text,
                "confidence_score": round(random.uniform(0.7, 0.95), 2),
                "participant_count": random.randint(5, 25),
                "status": random.choice(["validated", "pending_review", "validated", "validated"]),
                "is_anonymized": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            insights.append(insight)
    
    await db.insights.insert_many(insights)
    print(f"✅ {len(insights)} insights generados")
    return insights

async def create_initiatives(campaigns, tenant_id):
    """Crear iniciativas basadas en insights"""
    initiatives = []
    
    initiative_templates = [
        {"title": "Programa de Bienestar Laboral", "description": "Implementar programa integral de bienestar para reducir estrés y mejorar satisfacción.", "category": "clima_laboral"},
        {"title": "App Móvil B2B para Ferreterías", "description": "Desarrollar aplicación móvil para pedidos y seguimiento de envíos.", "category": "digital"},
        {"title": "Dashboard de Producción en Tiempo Real", "description": "Implementar sistema de monitoreo de producción integrado con e-commerce.", "category": "digital"},
        {"title": "Línea de Tornillería Sostenible", "description": "Desarrollar línea de productos eco-friendly para el mercado de construcción verde.", "category": "innovacion"},
        {"title": "Programa de Certificación en Seguridad", "description": "Certificar al personal en normas de seguridad industrial actualizadas.", "category": "seguridad"},
        {"title": "Integración ERP con Ferreterías", "description": "Desarrollar APIs para integración con sistemas de ferreterías mayoristas.", "category": "digital"},
        {"title": "Comunidad de Práctica Comercial", "description": "Crear espacio de intercambio de mejores prácticas entre equipo comercial.", "category": "clima_laboral"},
        {"title": "Automatización de Cotizaciones", "description": "Implementar cotizador automático con IA para pedidos personalizados.", "category": "innovacion"}
    ]
    
    for template in initiative_templates:
        reach = random.randint(50, 100)
        impact = random.randint(6, 10)
        confidence = random.randint(5, 10)
        effort = random.randint(3, 10)
        
        rice_score = (reach * impact * confidence) / effort
        ice_score = impact * confidence / effort * 10
        
        initiative = {
            "id": str(uuid.uuid4()),
            "campaign_id": campaigns[0]["id"],
            "tenant_id": tenant_id,
            "title": template["title"],
            "description": template["description"],
            "category": template["category"],
            "status": random.choice(["proposed", "approved", "in_progress", "proposed"]),
            "priority_method": random.choice(["RICE", "ICE"]),
            "reach": reach,
            "impact": impact,
            "confidence": confidence,
            "effort": effort,
            "rice_score": round(rice_score, 2),
            "ice_score": round(ice_score, 2),
            "priority_score": round(rice_score, 2),
            "owner_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        initiatives.append(initiative)
    
    await db.initiatives.insert_many(initiatives)
    print(f"✅ {len(initiatives)} iniciativas creadas")
    return initiatives

async def create_consents(users, tenant_id):
    """Crear registros de consentimiento"""
    consents = []
    participants = [u for u in users if u["role"] == "participant"]
    
    for user in participants:
        consent = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "tenant_id": tenant_id,
            "consent_type": "participation",
            "granted": True,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "ip_address": f"192.168.1.{random.randint(1, 254)}",
            "consent_text": "Acepto participar voluntariamente en esta investigación y autorizo el uso de mis respuestas de forma anónima.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        consents.append(consent)
    
    await db.consents.insert_many(consents)
    print(f"✅ {len(consents)} consentimientos registrados")

async def create_audit_logs(users, campaigns, tenant_id):
    """Crear logs de auditoría"""
    audit_logs = []
    
    actions = ["login", "view_transcript", "view_insight", "export_data", "consent_given"]
    
    for _ in range(50):
        user = random.choice(users)
        action = random.choice(actions)
        
        log = {
            "id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user["id"],
            "user_role": user["role"],
            "action": action,
            "resource_type": "session" if action in ["view_transcript"] else "insight" if action == "view_insight" else "auth",
            "resource_id": str(uuid.uuid4()),
            "details": {"action": action, "ip": f"192.168.1.{random.randint(1, 254)}"},
            "ip_address": f"192.168.1.{random.randint(1, 254)}",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 100))).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        audit_logs.append(log)
    
    await db.audit_logs.insert_many(audit_logs)
    print(f"✅ {len(audit_logs)} registros de auditoría creados")

async def main():
    print("\n" + "="*60)
    print("🏭 SIMULACIÓN DE PILOTO - ACME TORNILLOS S.A.S")
    print("="*60 + "\n")
    
    # Verificar si ya existe ACME
    existing = await db.tenants.find_one({"name": TENANT_NAME})
    if existing:
        print(f"⚠️  El tenant {TENANT_NAME} ya existe. Eliminando datos anteriores...")
        tenant_id = existing["id"]
        await db.users.delete_many({"tenant_id": tenant_id})
        await db.campaigns.delete_many({"tenant_id": tenant_id})
        await db.scripts.delete_many({"tenant_id": tenant_id})
        await db.sessions.delete_many({"tenant_id": tenant_id})
        await db.messages.delete_many({})
        await db.insights.delete_many({"tenant_id": tenant_id})
        await db.initiatives.delete_many({"tenant_id": tenant_id})
        await db.consents.delete_many({"tenant_id": tenant_id})
        await db.audit_logs.delete_many({"tenant_id": tenant_id})
        await db.tenants.delete_one({"id": tenant_id})
        print("✅ Datos anteriores eliminados\n")
    
    # Crear datos
    tenant_id = await create_tenant()
    users = await create_users(tenant_id)
    campaigns = await create_campaigns(tenant_id)
    scripts = await create_scripts(campaigns)
    sessions = await create_sessions_and_messages(campaigns, users, tenant_id)
    insights = await create_insights(campaigns, tenant_id)
    initiatives = await create_initiatives(campaigns, tenant_id)
    await create_consents(users, tenant_id)
    await create_audit_logs(users, campaigns, tenant_id)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DEL PILOTO ACME")
    print("="*60)
    print(f"""
    🏢 Empresa: {TENANT_NAME}
    📍 País: Colombia
    🏭 Industria: Manufactura - Tornillería B2B
    
    👥 Participantes: 100 colaboradores
       - Mercadeo: 20
       - Comercial: 25
       - Dirección Financiera: 15
       - Producción: 25
       - Tecnología: 15
    
    📋 Campañas: {len(campaigns)}
       - Diagnóstico Clima Organizacional 2025 (Activa)
       - Transformación Digital B2B (Activa)
       - Innovación en Productos (Borrador)
       - Cultura de Seguridad Industrial (Borrador)
    
    💬 Sesiones de chat: {len(sessions)}
    💡 Insights generados: {len(insights)}
    🎯 Iniciativas propuestas: {len(initiatives)}
    
    🔐 CREDENCIALES DE ACCESO:
       Admin ACME: admin@acme.com.co / acme2025
       Facilitador: facilitador@acme.com.co / acme2025
       Participantes: [nombre].[apellido]@acme.com.co / acme2025
    """)
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
