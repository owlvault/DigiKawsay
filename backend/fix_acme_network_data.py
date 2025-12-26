"""
Fix ACME network data - Add transcripts and taxonomy categories
"""
import asyncio
import random
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["test_database"]

# Categorías de taxonomía para ACME
TAXONOMY_CATEGORIES = [
    {"name": "Clima Laboral", "type": "theme", "color": "#3B82F6", "description": "Temas relacionados con el ambiente de trabajo"},
    {"name": "Comunicación", "type": "theme", "color": "#10B981", "description": "Aspectos de comunicación interna"},
    {"name": "Carga de Trabajo", "type": "tension", "color": "#EF4444", "description": "Tensiones por exceso de trabajo"},
    {"name": "Transformación Digital", "type": "opportunity", "color": "#8B5CF6", "description": "Oportunidades de digitalización"},
    {"name": "Plataforma B2B", "type": "theme", "color": "#F59E0B", "description": "Temas de la plataforma de e-commerce"},
    {"name": "Innovación", "type": "opportunity", "color": "#EC4899", "description": "Ideas y propuestas innovadoras"},
    {"name": "Seguridad Industrial", "type": "theme", "color": "#6366F1", "description": "Temas de seguridad en planta"},
    {"name": "Capacitación", "type": "opportunity", "color": "#14B8A6", "description": "Necesidades de formación"},
    {"name": "Liderazgo", "type": "theme", "color": "#F97316", "description": "Aspectos de liderazgo y gestión"},
    {"name": "Bienestar", "type": "symbol", "color": "#84CC16", "description": "Bienestar del colaborador"},
    {"name": "Clientes", "type": "theme", "color": "#0EA5E9", "description": "Relación con ferreterías clientes"},
    {"name": "Producción", "type": "theme", "color": "#A855F7", "description": "Procesos de manufactura"},
]

async def main():
    print("="*60)
    print("🔧 CORRIGIENDO DATOS DE RED PARA ACME")
    print("="*60)
    
    # Get ACME tenant
    tenant = await db.tenants.find_one({"name": {"$regex": "ACME"}})
    if not tenant:
        print("❌ No se encontró tenant ACME")
        return
    
    tenant_id = tenant["id"]
    print(f"✅ Tenant encontrado: {tenant['name']}")
    
    # Create taxonomy categories
    existing_cats = await db.taxonomy_categories.count_documents({"tenant_id": tenant_id})
    if existing_cats == 0:
        categories = []
        for cat in TAXONOMY_CATEGORIES:
            categories.append({
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "name": cat["name"],
                "type": cat["type"],
                "color": cat["color"],
                "description": cat["description"],
                "is_active": True,
                "usage_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        await db.taxonomy_categories.insert_many(categories)
        print(f"✅ {len(categories)} categorías de taxonomía creadas")
    else:
        print(f"ℹ️ Ya existen {existing_cats} categorías de taxonomía")
    
    # Get categories for linking
    categories = await db.taxonomy_categories.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    cat_map = {c["name"]: c["id"] for c in categories}
    
    # Get sessions
    sessions = await db.sessions.find({"tenant_id": tenant_id, "status": "completed"}, {"_id": 0}).to_list(500)
    print(f"📋 Sesiones completadas encontradas: {len(sessions)}")
    
    # Create transcripts from sessions
    existing_transcripts = await db.transcripts.count_documents({"tenant_id": tenant_id})
    if existing_transcripts == 0:
        transcripts = []
        for session in sessions:
            # Get messages for this session
            messages = await db.messages.find({"session_id": session["id"]}).to_list(100)
            
            # Build transcript content
            content = ""
            for msg in messages:
                role = "VAL" if msg.get("role") == "assistant" else "Participante"
                content += f"{role}: {msg.get('content', '')}\n\n"
            
            # Get user to find pseudonym
            user = await db.users.find_one({"id": session.get("participant_id")}, {"_id": 0})
            pseudonym_id = user.get("pseudonym_id") if user else session.get("participant_pseudonym", f"P-{uuid.uuid4().hex[:8].upper()}")
            
            transcript = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "campaign_id": session.get("campaign_id"),
                "session_id": session["id"],
                "pseudonym_id": pseudonym_id,
                "content": content,
                "word_count": len(content.split()),
                "is_anonymized": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            transcripts.append(transcript)
        
        if transcripts:
            await db.transcripts.insert_many(transcripts)
            print(f"✅ {len(transcripts)} transcripciones creadas")
    else:
        print(f"ℹ️ Ya existen {existing_transcripts} transcripciones")
    
    # Get transcripts for linking insights
    transcripts = await db.transcripts.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(500)
    transcript_map = {t["session_id"]: t for t in transcripts}
    
    # Update insights with category_id and source_session_id
    insights = await db.insights.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(500)
    print(f"💡 Insights encontrados: {len(insights)}")
    
    # Category mapping based on insight category
    category_mapping = {
        "clima_laboral": ["Clima Laboral", "Comunicación", "Bienestar", "Liderazgo"],
        "digital": ["Transformación Digital", "Plataforma B2B", "Innovación"],
        "innovacion": ["Innovación", "Clientes", "Producción"],
        "seguridad": ["Seguridad Industrial", "Capacitación", "Bienestar"]
    }
    
    updated_count = 0
    for insight in insights:
        insight_cat = insight.get("category", "clima_laboral")
        possible_cats = category_mapping.get(insight_cat, ["Clima Laboral"])
        selected_cat_name = random.choice(possible_cats)
        category_id = cat_map.get(selected_cat_name)
        
        # Get a random session for this campaign
        campaign_sessions = [s for s in sessions if s.get("campaign_id") == insight.get("campaign_id")]
        source_session_id = None
        if campaign_sessions:
            selected_session = random.choice(campaign_sessions)
            source_session_id = selected_session["id"]
        
        # Update insight
        await db.insights.update_one(
            {"id": insight["id"]},
            {"$set": {
                "category_id": category_id,
                "source_session_id": source_session_id
            }}
        )
        updated_count += 1
    
    print(f"✅ {updated_count} insights actualizados con categorías y sesiones")
    
    # Update category usage counts
    for cat in categories:
        count = await db.insights.count_documents({"category_id": cat["id"]})
        await db.taxonomy_categories.update_one(
            {"id": cat["id"]},
            {"$set": {"usage_count": count}}
        )
    
    print(f"✅ Conteos de uso de categorías actualizados")
    
    # Verify data is ready for network generation
    print("\n" + "="*60)
    print("📊 VERIFICACIÓN DE DATOS PARA RED")
    print("="*60)
    
    transcripts_count = await db.transcripts.count_documents({"tenant_id": tenant_id})
    categories_count = await db.taxonomy_categories.count_documents({"tenant_id": tenant_id, "is_active": True})
    insights_with_cat = await db.insights.count_documents({"tenant_id": tenant_id, "category_id": {"$exists": True, "$ne": None}})
    insights_with_session = await db.insights.count_documents({"tenant_id": tenant_id, "source_session_id": {"$exists": True, "$ne": None}})
    
    print(f"   Transcripciones: {transcripts_count}")
    print(f"   Categorías activas: {categories_count}")
    print(f"   Insights con categoría: {insights_with_cat}")
    print(f"   Insights con sesión: {insights_with_session}")
    
    if transcripts_count > 0 and categories_count > 0 and insights_with_cat > 0:
        print("\n✅ ¡Datos listos para generar red!")
    else:
        print("\n⚠️ Faltan datos para la generación de red")

asyncio.run(main())
