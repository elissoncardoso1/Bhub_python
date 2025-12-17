"""
Modelo de categoria para classificação de artigos.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Category(BaseModel):
    """
    Categoria de artigos.
    Categorias padrão: Clínica, Educação, Organizacional, Pesquisa, Outros
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")  # Hex color

    # Keywords para classificação automática (separadas por vírgula)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Embedding pré-calculado para classificação ML (JSON serializado)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos
    articles: Mapped[list["Article"]] = relationship(
        "Article",
        back_populates="category",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"Category(id={self.id}, name={self.name}, slug={self.slug})"


# Dados iniciais das categorias
DEFAULT_CATEGORIES = [
    {
        "name": "Clínica",
        "slug": "clinica",
        "description": "Artigos relacionados à prática clínica em Análise do Comportamento",
        "color": "#10B981",
        "keywords": "clínica,terapia,tratamento,intervenção,paciente,cliente,sessão,consultório,atendimento,transtorno,diagnóstico,avaliação clínica,caso clínico,psicoterapia,clinical,therapy,treatment,intervention,patient,client,session,clinic,disorder,diagnosis,clinical assessment,clinical case",
    },
    {
        "name": "Educação",
        "slug": "educacao",
        "description": "Artigos sobre aplicações educacionais da Análise do Comportamento",
        "color": "#3B82F6",
        "keywords": "educação,ensino,escola,professor,aluno,aprendizagem,instrução,currículo,sala de aula,educacional,pedagógico,escolar,acadêmico,formação,education,teaching,school,teacher,student,learning,instruction,curriculum,classroom,educational,pedagogical,academic,training",
    },
    {
        "name": "Organizacional",
        "slug": "organizacional",
        "description": "Artigos sobre Análise do Comportamento em contextos organizacionais",
        "color": "#8B5CF6",
        "keywords": "organizacional,empresa,trabalho,gestão,liderança,produtividade,desempenho,feedback,treinamento corporativo,RH,recursos humanos,OBM,performance management,organizational,company,work,management,leadership,productivity,performance,feedback,corporate training,HR,human resources,OBM",
    },
    {
        "name": "Pesquisa",
        "slug": "pesquisa",
        "description": "Artigos de pesquisa básica e conceitual em Análise do Comportamento",
        "color": "#F59E0B",
        "keywords": "pesquisa,experimento,metodologia,dados,análise,resultados,hipótese,variável,controle,laboratório,estudo,investigação,empírico,experimental,básica,research,experiment,methodology,data,analysis,results,hypothesis,variable,control,laboratory,study,investigation,empirical,experimental,basic",
    },
    {
        "name": "Autismo",
        "slug": "autismo",
        "description": "Artigos sobre autismo, TEA e intervenções baseadas em ABA",
        "color": "#EC4899",
        "keywords": "autismo,TEA,transtorno do espectro autista,ASD,autism,spectrum,autistic,ABA para autismo,intervenção precoce,early intervention,autism spectrum disorder,autistic disorder,autism treatment,autism therapy,autism intervention,autism research",
    },
    {
        "name": "Behaviorismo Radical",
        "slug": "behaviorismo-radical",
        "description": "Artigos sobre filosofia, teoria e fundamentos do Behaviorismo Radical",
        "color": "#7C3AED",
        "keywords": "behaviorismo radical,radical behaviorism,skinner,filosofia,epistemologia,luta de classes,conceitual,teórico,fundamentos,história,seleção por consequências,cultura,ontogenia,filogenia,mentalsimo,pública,privada,eventos privados,filosofia da ciência",
    },
    {
        "name": "Comportamento Verbal",
        "slug": "comportamento-verbal",
        "description": "Artigos sobre linguagem e comportamento verbal (Skinner)",
        "color": "#059669",
        "keywords": "comportamento verbal,verbal behavior,tato,mando,intraverbal,ecoico,autoclítico,textual,transcrição,audiência,falante,ouvinte,linguagem,comunicação,relational frame theory,RFT,frames relacionais",
    },
    {
        "name": "Notícias",
        "slug": "noticias",
        "description": "Notícias e atualidades sobre Análise do Comportamento",
        "color": "#06B6D4",
        "keywords": "notícias,news,atualidades,atualizações,updates,breaking news,announcements,events,eventos,anúncios,novidades,latest,recent",
    },
    {
        "name": "Outros",
        "slug": "outros",
        "description": "Artigos que não se enquadram nas outras categorias",
        "color": "#6B7280",
        "keywords": "",
    },
]
