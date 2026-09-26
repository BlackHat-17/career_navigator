"""
SkillTaxonomy
─────────────
Single source of truth for every skill the Evidence Matching engine knows
about, plus the signals used to detect that skill in two very different
places:

  1. Resume text            → simple alias matching
  2. A live GitHub repo     → language stats, dependency manifests,
                               well-known filenames, repo topics, and
                               description/README keywords

Also holds ROLE_SKILL_MAP: which skills matter for a given target role
(e.g. "Database Engineer" → SQL, PostgreSQL, MongoDB, ...), plus a small
keyword resolver so free-text roles typed by the user ("Database Engineer",
"DB Engineer", "backend dev") map onto one of the known role profiles.

Everything here is intentionally data, not logic — `github_evidence_service`
and `resume_skill_service` do the actual scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class SkillSignal:
    id: str
    name: str
    # words/phrases that count as a match inside free-text (resume, README, description)
    aliases: List[str] = field(default_factory=list)
    # GitHub "language" values (from the /languages endpoint) that count as strong evidence
    languages: List[str] = field(default_factory=list)
    # substrings to look for inside dependency manifests (requirements.txt, package.json, ...)
    dependencies: List[str] = field(default_factory=list)
    # substrings to look for in the repo's file tree (case-insensitive)
    filenames: List[str] = field(default_factory=list)
    # GitHub repo "topics" that count as an explicit, author-declared match
    topics: List[str] = field(default_factory=list)


def _s(id_: str, name: str, **kwargs) -> SkillSignal:
    return SkillSignal(id=id_, name=name, **kwargs)


SKILL_TAXONOMY: Dict[str, SkillSignal] = {
    s.id: s
    for s in [
        # ── Languages ────────────────────────────────────────────────────────
        _s("python", "Python", aliases=["python"], languages=["Python"],
           filenames=["requirements.txt", "pyproject.toml", "pipfile", "setup.py"]),
        _s("javascript", "JavaScript", aliases=["javascript", "js"], languages=["JavaScript"],
           filenames=["package.json"]),
        _s("typescript", "TypeScript", aliases=["typescript", "ts"], languages=["TypeScript"],
           filenames=["tsconfig.json"]),
        _s("java", "Java", aliases=["java"], languages=["Java"],
           filenames=["pom.xml", "build.gradle"]),
        _s("cpp", "C++", aliases=["c++", "cpp"], languages=["C++"]),
        _s("c", "C", aliases=[" c programming", "c language"], languages=["C"]),
        _s("csharp", "C#", aliases=["c#", ".net", "csharp"], languages=["C#"],
           filenames=[".csproj"]),
        _s("go", "Go", aliases=["golang", "go lang", "go programming"], languages=["Go"],
           filenames=["go.mod"]),
        _s("rust", "Rust", aliases=["rust"], languages=["Rust"], filenames=["cargo.toml"]),
        _s("ruby", "Ruby", aliases=["ruby"], languages=["Ruby"], filenames=["gemfile"]),
        _s("php", "PHP", aliases=["php"], languages=["PHP"], filenames=["composer.json"]),
        _s("kotlin", "Kotlin", aliases=["kotlin"], languages=["Kotlin"]),
        _s("swift", "Swift", aliases=["swift"], languages=["Swift"]),
        _s("html", "HTML", aliases=["html", "html5"], languages=["HTML"]),
        _s("css", "CSS", aliases=["css", "css3"], languages=["CSS"]),
        _s("shell", "Shell Scripting", aliases=["bash", "shell scripting"], languages=["Shell"]),
        _s("r_lang", "R", aliases=[" r programming", " r language"], languages=["R"]),

        # ── Web / backend frameworks ─────────────────────────────────────────
        _s("django", "Django", aliases=["django"], dependencies=["django"], topics=["django"]),
        _s("flask", "Flask", aliases=["flask"], dependencies=["flask"], topics=["flask"]),
        _s("fastapi", "FastAPI", aliases=["fastapi"], dependencies=["fastapi"], topics=["fastapi"]),
        _s("express", "Express.js", aliases=["express.js", "expressjs", "express"],
           dependencies=["express"], topics=["express", "expressjs"]),
        _s("nodejs", "Node.js", aliases=["node.js", "nodejs", "node js"],
           dependencies=["node"], topics=["nodejs", "node"], filenames=["package.json"]),
        _s("spring", "Spring / Spring Boot", aliases=["spring boot", "spring framework", "spring"],
           dependencies=["springframework", "spring-boot"], topics=["spring-boot", "spring"]),
        _s("react", "React", aliases=["react.js", "reactjs", "react"], dependencies=['"react"'],
           topics=["react", "reactjs"]),
        _s("vue", "Vue.js", aliases=["vue.js", "vuejs", "vue"], dependencies=['"vue"'],
           topics=["vue", "vuejs"]),
        _s("angular", "Angular", aliases=["angular"], dependencies=["@angular/core"],
           topics=["angular"]),
        _s("nextjs", "Next.js", aliases=["next.js", "nextjs"], dependencies=['"next"'],
           topics=["nextjs", "next-js"]),
        _s("graphql", "GraphQL", aliases=["graphql"], dependencies=["graphql"], topics=["graphql"]),
        _s("rest_api", "REST API Design", aliases=["rest api", "restful", "rest apis"],
           topics=["rest-api", "restful-api"]),
        _s("microservices", "Microservices", aliases=["microservice", "microservices"],
           topics=["microservices", "microservice"]),

        # ── Data / ML ────────────────────────────────────────────────────────
        _s("pandas", "Pandas", aliases=["pandas"], dependencies=["pandas"]),
        _s("numpy", "NumPy", aliases=["numpy"], dependencies=["numpy"]),
        _s("scikit_learn", "scikit-learn", aliases=["scikit-learn", "sklearn"],
           dependencies=["scikit-learn", "sklearn"]),
        _s("tensorflow", "TensorFlow", aliases=["tensorflow"], dependencies=["tensorflow"],
           topics=["tensorflow"]),
        _s("pytorch", "PyTorch", aliases=["pytorch"], dependencies=["torch"], topics=["pytorch"]),
        _s("machine_learning", "Machine Learning", aliases=["machine learning", " ml ", "ml engineer"],
           topics=["machine-learning", "ml"]),
        _s("deep_learning", "Deep Learning", aliases=["deep learning"], topics=["deep-learning"]),
        _s("nlp", "NLP", aliases=["nlp", "natural language processing"], topics=["nlp"]),
        _s("computer_vision", "Computer Vision", aliases=["computer vision", "opencv"],
           dependencies=["opencv"], topics=["computer-vision"]),
        _s("mlops", "MLOps", aliases=["mlops"], topics=["mlops"]),
        _s("data_engineering", "Data Engineering", aliases=["data engineering", "etl"],
           topics=["data-engineering", "etl"]),
        _s("spark", "Apache Spark", aliases=["spark", "pyspark"], dependencies=["pyspark", "spark"],
           topics=["spark", "apache-spark"]),
        _s("kafka", "Apache Kafka", aliases=["kafka"], dependencies=["kafka"], topics=["kafka"]),
        _s("airflow", "Apache Airflow", aliases=["airflow"], dependencies=["airflow"],
           topics=["airflow"]),

        # ── Databases ────────────────────────────────────────────────────────
        _s("sql", "SQL", aliases=["sql", "structured query language"],
           dependencies=["sqlalchemy", "psycopg2", "mysqlclient", "sequelize", "jdbc"],
           topics=["sql"]),
        _s("postgresql", "PostgreSQL", aliases=["postgresql", "postgres"],
           dependencies=["psycopg2", "postgres", "pg "], topics=["postgresql", "postgres"]),
        _s("mysql", "MySQL", aliases=["mysql"], dependencies=["mysql", "mysqlclient"],
           topics=["mysql"]),
        _s("mongodb", "MongoDB", aliases=["mongodb", "mongo"],
           dependencies=["pymongo", "mongoose", "mongodb"], topics=["mongodb"]),
        _s("redis", "Redis", aliases=["redis"], dependencies=["redis"], topics=["redis"]),
        _s("nosql", "NoSQL", aliases=["nosql"], topics=["nosql"]),
        _s("database_design", "Database Design", aliases=["database design", "data modeling",
                                                            "schema design", "normalization"],
           topics=["database-design"]),
        _s("elasticsearch", "Elasticsearch", aliases=["elasticsearch", "elastic search"],
           dependencies=["elasticsearch"], topics=["elasticsearch"]),

        # ── DevOps / Cloud ───────────────────────────────────────────────────
        _s("docker", "Docker", aliases=["docker"], filenames=["dockerfile", "docker-compose.yml",
                                                                "docker-compose.yaml"],
           topics=["docker"]),
        _s("kubernetes", "Kubernetes", aliases=["kubernetes", "k8s"],
           filenames=["k8s", "kubernetes", "helm"], topics=["kubernetes", "k8s"]),
        _s("ci_cd", "CI/CD", aliases=["ci/cd", "continuous integration", "continuous deployment"],
           filenames=[".github/workflows", ".gitlab-ci.yml", "jenkinsfile", ".circleci"],
           topics=["ci-cd", "cicd"]),
        _s("terraform", "Terraform", aliases=["terraform"], filenames=[".tf"],
           dependencies=["terraform"], topics=["terraform"]),
        _s("aws", "AWS", aliases=["aws", "amazon web services"], dependencies=["boto3", "aws-sdk"],
           topics=["aws"]),
        _s("gcp", "Google Cloud (GCP)", aliases=["gcp", "google cloud"],
           dependencies=["google-cloud"], topics=["gcp", "google-cloud"]),
        _s("azure", "Azure", aliases=["azure"], dependencies=["azure-"], topics=["azure"]),
        _s("linux", "Linux", aliases=["linux"], topics=["linux"]),
        _s("git", "Git / Version Control", aliases=["git", "version control"],
           filenames=[".gitignore"]),
    ]
}

# Aliases must never collide across skills in a way that breaks resume matching;
# each alias is only ever looked up for its own skill, so overlaps are fine.


# ── Role → required-skill profiles ──────────────────────────────────────────

ROLE_SKILL_MAP: Dict[str, List[str]] = {
    "database_engineer": [
        "sql", "postgresql", "mysql", "mongodb", "redis", "database_design",
        "nosql", "elasticsearch", "data_engineering", "python",
    ],
    "data_engineer": [
        "python", "sql", "spark", "kafka", "airflow", "data_engineering",
        "postgresql", "mongodb", "aws", "docker",
    ],
    "ml_engineer": [
        "python", "machine_learning", "tensorflow", "pytorch", "scikit_learn",
        "pandas", "numpy", "docker", "mlops", "sql", "rest_api",
    ],
    "data_scientist": [
        "python", "pandas", "numpy", "scikit_learn", "machine_learning",
        "sql", "deep_learning", "nlp", "r_lang",
    ],
    "backend_developer": [
        "python", "java", "nodejs", "rest_api", "sql", "postgresql", "mongodb",
        "docker", "git", "microservices", "ci_cd",
    ],
    "frontend_developer": [
        "javascript", "typescript", "react", "html", "css", "nextjs", "git",
        "rest_api",
    ],
    "full_stack_developer": [
        "javascript", "typescript", "react", "nodejs", "express", "sql",
        "mongodb", "html", "css", "git", "rest_api", "docker",
    ],
    "devops_engineer": [
        "docker", "kubernetes", "ci_cd", "terraform", "aws", "linux", "git",
        "python", "shell",
    ],
    "cloud_engineer": [
        "aws", "gcp", "azure", "terraform", "docker", "kubernetes", "linux",
        "ci_cd",
    ],
    "mobile_developer": [
        "kotlin", "swift", "java", "rest_api", "git",
    ],
    "software_engineer": [
        "python", "javascript", "sql", "git", "rest_api", "docker", "ci_cd",
    ],
}

# (keywords, role_key) — first match wins; order matters (most specific first)
_ROLE_KEYWORDS: List[tuple[List[str], str]] = [
    (["database engineer", "db engineer", "dba", "database administrator"], "database_engineer"),
    (["data engineer"], "data_engineer"),
    (["machine learning engineer", "ml engineer", "ai engineer"], "ml_engineer"),
    (["data scientist"], "data_scientist"),
    (["devops", "site reliability", "sre"], "devops_engineer"),
    (["cloud engineer"], "cloud_engineer"),
    (["full stack", "fullstack", "full-stack"], "full_stack_developer"),
    (["frontend", "front-end", "front end", "ui developer"], "frontend_developer"),
    (["backend", "back-end", "back end"], "backend_developer"),
    (["mobile developer", "android developer", "ios developer"], "mobile_developer"),
]


def resolve_role_key(target_role: str) -> str:
    """Map a free-text role string onto one of the known ROLE_SKILL_MAP keys."""
    normalized = f" {target_role.lower().strip()} "
    for keywords, role_key in _ROLE_KEYWORDS:
        if any(kw in normalized for kw in keywords):
            return role_key
    return "software_engineer"


def resolve_role_skills(target_role: str) -> List[str]:
    role_key = resolve_role_key(target_role)
    return ROLE_SKILL_MAP[role_key]


def skill_display_name(skill_id: str) -> str:
    signal = SKILL_TAXONOMY.get(skill_id)
    return signal.name if signal else skill_id
