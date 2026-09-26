"""
AgenticAnalyzer
───────────────
Uses Gemini with agentic AI capabilities to perform intelligent analysis.
Replaces the rigid microservices architecture with flexible AI reasoning.

This service:
- Uses Gemini API directly for AI analysis
- Leverages GitHub API (will be MCP later) for repository data
- Makes autonomous decisions about analysis strategy
- Provides reasoning traces for explainability
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from google import genai
from google.genai import types
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Configure Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


class AgenticAnalyzer:
    """
    Agentic AI analyzer using Gemini for intelligent, autonomous analysis.
    """
    
    def __init__(self):
        self.model_id = settings.GEMINI_MODEL
    
    async def analyze_resume(
        self,
        resume_text: str,
        target_role: str,
        job_description: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze resume using Gemini AI.
        Extracts skills, experience, and qualifications.
        """
        logger.info("[AgenticAI] Analyzing resume for role: %s", target_role)
        
        prompt = f"""You are an expert technical recruiter and career advisor. Analyze this resume for the target role.

Target Role: {target_role}
Job Description: {job_description or "Not provided"}

Resume:
{resume_text}

Extract and return a JSON object with:
{{
  "claimed_skills": [
    {{"name": "skill name", "context": "where it's mentioned", "confidence": 0.0-1.0}}
  ],
  "experience_years": estimated years of experience,
  "education": education background,
  "summary": brief candidate summary
}}

Focus on technical skills, frameworks, languages, tools, and methodologies.
Be precise and only extract skills explicitly mentioned or clearly demonstrated.
"""
        
        try:
            response = client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            result_text = response.text.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            logger.info("[AgenticAI] Resume analysis complete: %d skills found", len(result.get("claimed_skills", [])))
            return result
            
        except Exception as e:
            logger.error("[AgenticAI] Resume analysis failed: %s", e)
            # Return minimal fallback
            return {
                "claimed_skills": [],
                "experience_years": 0,
                "education": "Not specified",
                "summary": f"Analysis failed: {str(e)}"
            }
    
    async def cross_reference_skills(
        self,
        github_data: Dict[str, Any],
        resume_data: Dict[str, Any],
        target_role: str,
        job_description: str = "",
    ) -> Dict[str, Any]:
        """
        Cross-reference GitHub evidence with resume claims using AI reasoning.
        Classifies skills as verified, partial, missing, or unsupported.
        """
        logger.info("[AgenticAI] Cross-referencing skills for role: %s", target_role)
        
        # Format GitHub skills
        github_skills_text = "\n".join([
            f"- {s['name']}: {', '.join(s.get('evidence', ['no evidence']))}"
            for s in github_data.get("skills", [])
        ])
        
        # Format resume skills
        resume_skills_text = "\n".join([
            f"- {s['name']}: {s.get('context', 'mentioned in resume')}"
            for s in resume_data.get("claimed_skills", [])
        ])
        
        prompt = f"""You are an expert technical recruiter analyzing a candidate's profile.

Target Role: {target_role}
Job Description: {job_description or "Not provided"}

GitHub Skills (from code analysis):
{github_skills_text or "No GitHub data available"}

Resume Skills (claimed):
{resume_skills_text or "No resume skills found"}

Classify each skill into these categories:

1. **VERIFIED**: Strong evidence in BOTH GitHub code AND resume
2. **PARTIAL**: Claimed in resume but limited/weak code evidence
3. **MISSING**: Required for the target role but NOT found in profile
4. **UNSUPPORTED**: Claimed in resume but NO code evidence

Return JSON:
{{
  "verified_skills": [
    {{"name": "skill", "confidence": 0.0-1.0, "evidence": ["github: ...", "resume: ..."]}}
  ],
  "partial_skills": [
    {{"name": "skill", "confidence": 0.0-1.0, "evidence": ["limited evidence"]}}
  ],
  "missing_skills": [
    {{"name": "skill", "confidence": 0.0-1.0, "evidence": ["required for role"]}}
  ],
  "unsupported_claims": [
    {{"name": "skill", "confidence": 0.0-1.0, "evidence": ["claimed without proof"]}}
  ]
}}

Be thorough and consider:
- Code quality and complexity in GitHub
- Frequency of skill usage
- Recency of projects
- Job requirements vs candidate skills
"""
        
        try:
            response = client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            result_text = response.text.strip()
            
            # Extract JSON from markdown
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            verified_count = len(result.get("verified_skills", []))
            partial_count = len(result.get("partial_skills", []))
            missing_count = len(result.get("missing_skills", []))
            
            logger.info(
                "[AgenticAI] Skill classification: %d verified, %d partial, %d missing",
                verified_count, partial_count, missing_count
            )
            
            return result
            
        except Exception as e:
            logger.error("[AgenticAI] Skill cross-reference failed: %s", e)
            # Fallback: basic classification
            return {
                "verified_skills": resume_data.get("claimed_skills", [])[:3],
                "partial_skills": [],
                "missing_skills": [],
                "unsupported_claims": []
            }
    
    async def recommend_projects(
        self,
        career_goal: str,
        verified_skills: List[str],
        skill_gaps: List[str],
    ) -> Dict[str, Any]:
        """
        Generate personalized project recommendations using AI.
        """
        logger.info("[AgenticAI] Generating project recommendations")
        
        prompt = f"""You are an expert technical mentor. Generate personalized project recommendations.

Career Goal: {career_goal}
Current Skills: {', '.join(verified_skills) if verified_skills else 'None'}
Skill Gaps to Address: {', '.join(skill_gaps) if skill_gaps else 'None'}

Generate 3-5 project ideas that will help close the skill gaps while building on existing strengths.

Return JSON:
{{
  "recommendations": [
    {{
      "title": "project title",
      "description": "what to build",
      "skills": ["skill1", "skill2"],
      "difficulty": "beginner|intermediate|advanced",
      "reason": "why this project",
      "estimated_hours": estimated time
    }}
  ]
}}

Make projects:
- Practical and portfolio-worthy
- Progressive in difficulty
- Focused on 2-3 skills each
- Realistic in scope
"""
        
        try:
            response = client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            logger.info("[AgenticAI] Generated %d project recommendations", len(result.get("recommendations", [])))
            return result
            
        except Exception as e:
            logger.error("[AgenticAI] Project recommendation failed: %s", e)
            return {"recommendations": []}
    
    async def generate_roadmap(
        self,
        career_goal: str,
        current_skills: List[str],
        skill_gaps: List[str],
        recommended_projects: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a week-by-week learning roadmap using AI.
        """
        logger.info("[AgenticAI] Generating learning roadmap")
        
        prompt = f"""You are an expert technical career advisor. Create a detailed learning roadmap.

Career Goal: {career_goal}
Current Skills: {', '.join(current_skills) if current_skills else 'Starting from basics'}
Skills to Learn: {', '.join(skill_gaps) if skill_gaps else 'General upskilling'}
Project Ideas: {', '.join(recommended_projects) if recommended_projects else 'TBD'}

Create a 12-week roadmap with weekly objectives.

Return JSON:
{{
  "summary": "overview of the roadmap",
  "total_weeks": 12,
  "roadmap": [
    {{
      "week": 1,
      "topic": "main topic",
      "description": "what to learn and do",
      "resources": ["resource 1", "resource 2"],
      "milestone": "what to complete",
      "skills_covered": ["skill1"],
      "priority": "high|medium|low"
    }}
  ]
}}

Make it:
- Progressive (basics → advanced)
- Practical (hands-on projects)
- Realistic (achievable weekly goals)
- Resource-rich (docs, tutorials, courses)
"""
        
        try:
            response = client.models.generate_content(
                model=self.model_id,
                contents=prompt,
            )
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            logger.info("[AgenticAI] Generated %d-week roadmap", len(result.get("roadmap", [])))
            return result
            
        except Exception as e:
            logger.error("[AgenticAI] Roadmap generation failed: %s", e)
            return {
                "summary": "Failed to generate roadmap",
                "total_weeks": 0,
                "roadmap": []
            }
