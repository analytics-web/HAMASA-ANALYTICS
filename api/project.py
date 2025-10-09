from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from api.deps import require_role
from models.project import MediaCategory, Project,ProjectCategory, ProjectThematicAreas, MediaSource, ReportAvenue, ReportTime, ReportConsultation
from models.client_user import ClientUser
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])

# Create a project
@router.post("/", response_model=ProjectOut)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ]))
):
    # Create project
    new_project = Project(
        title=project.title,
        description=project.description,
        client_id=project.client_id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Assign categories
    if project.category_ids:
        new_project.categories = db.query(ProjectCategory).filter(
            ProjectCategory.id.in_(project.category_ids)
        ).all()

    # Create and assign thematic areas (instead of linking existing IDs)
    if project.thematic_areas:
        created_thematic_areas = []
        for area in project.thematic_areas:
            new_area = ProjectThematicAreas(
                area=area.area,
                title=area.title,
                description=area.description,
                monitoring_objective=area.monitoring_objective
            )
            db.add(new_area)
            created_thematic_areas.append(new_area)
        db.commit()  # commit thematic areas first so they get IDs
        for ta in created_thematic_areas:
            db.refresh(ta)
        new_project.thematic_areas.extend(created_thematic_areas)

    # Assign collaborators
    if project.collaborator_ids:
        new_project.collaborators = db.query(ClientUser).filter(
            ClientUser.id.in_(project.collaborator_ids)
        ).all()

    # Assign media sources
    if project.media_source_ids:
        new_project.media_sources = db.query(MediaSource).filter(
            MediaSource.id.in_(project.media_source_ids)
        ).all()

    # Assign report links
    if project.report_avenue_ids:
        new_project.report_avenues = db.query(ReportAvenue).filter(
            ReportAvenue.id.in_(project.report_avenue_ids)
        ).all()

    if project.report_time_ids:
        new_project.report_times = db.query(ReportTime).filter(
            ReportTime.id.in_(project.report_time_ids)
        ).all()

    if project.report_consultation_ids:
        new_project.report_consultations = db.query(ReportConsultation).filter(
            ReportConsultation.id.in_(project.report_consultation_ids)
        ).all()

    db.commit()
    db.refresh(new_project)

    return new_project






# Read all projects
@router.get("/", response_model=List[ProjectOut])
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

# Read single project
@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

# Update project
@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, project: ProjectUpdate, db: Session = Depends(get_db)):
    existing_project = db.query(Project).filter(Project.id == project_id).first()
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for field, value in project.dict(exclude_unset=True).items():
        if hasattr(existing_project, field):
            setattr(existing_project, field, value)
    
    db.commit()
    db.refresh(existing_project)
    return existing_project

# Delete project
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return



# Create Categories all admins and client admin
@router.post("/categories/", response_model=ProjectCategoryOut)
def create_category(
        category: ProjectCategoryCreate, 
        current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin, UserRole.reviewer])), 
        db: Session = Depends(get_db)
    ):
    
    
    new_cat = ProjectCategory(category=category.category)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


# get all categories
@router.get("/categories/", response_model=List[ProjectCategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(ProjectCategory).all()

# create Thematic Areas all admins 
@router.post("/thematic-areas/", response_model=ProjectThematicAreaOut)
def create_thematic_area(
        area: ProjectThematicAreaCreate,
        current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin, UserRole.reviewer, UserRole.data_clerk, UserRole.org_user])),  
        db: Session = Depends(get_db)
    ):
    new_area = ProjectThematicAreas(
        area=area.area,
        title=area.title,
        description=area.description,
        monitoring_objective=area.monitoring_objective
    )
    db.add(new_area)
    db.commit()
    db.refresh(new_area)
    return new_area

# get all thematic areas
@router.get("/thematic-areas/", response_model=List[ProjectThematicAreaOut])
def get_thematic_areas(db: Session = Depends(get_db)):
    return db.query(ProjectThematicAreas).all()



# Media Categories
@router.post("/media-categories/", response_model=MediaCategoryOut)
def create_media_category(
        category: MediaCategoryBase,
        current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin, UserRole.reviewer, UserRole.data_clerk, UserRole.org_user])),   
        db: Session = Depends(get_db)
    ):
    new_cat = MediaCategory(name=category.name)
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat

@router.get("/media-categories/", response_model=List[MediaCategoryOut])
def get_media_categories(db: Session = Depends(get_db)):
    return db.query(MediaCategory).all()

# Media Sources
@router.post("/media-sources/", response_model=MediaSourceOut)
def create_media_source(
    source: MediaSourceBase, db: Session = Depends(get_db)):
    new_source = MediaSource(name=source.name, category_id=source.category_id)
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@router.get("/media-sources/", response_model=List[MediaSourceOut])
def get_media_sources(db: Session = Depends(get_db)):
    return db.query(MediaSource).all()



# Report Avenues
@router.post("/reports/avenues/", response_model=ReportAvenueOut)
def create_report_avenue(avenue: ReportAvenueBase, db: Session = Depends(get_db)):
    new_avenue = ReportAvenue(name=avenue.name)
    db.add(new_avenue)
    db.commit()
    db.refresh(new_avenue)
    return new_avenue

@router.get("/reports/avenues/", response_model=List[ReportAvenueOut])
def get_report_avenues(db: Session = Depends(get_db)):
    return db.query(ReportAvenue).all()

# Report Times
@router.post("/reports/times/", response_model=ReportTimeOut)
def create_report_time(time: ReportTimeBase, db: Session = Depends(get_db)):
    new_time = ReportTime(name=time.name)
    db.add(new_time)
    db.commit()
    db.refresh(new_time)
    return new_time

@router.get("/reports/times/", response_model=List[ReportTimeOut])
def get_report_times(db: Session = Depends(get_db)):
    return db.query(ReportTime).all()

# Report Consultations
@router.post("/reports/consultations/", response_model=ReportConsultationOut)
def create_report_consultation(cons: ReportConsultationBase, db: Session = Depends(get_db)):
    new_cons = ReportConsultation(name=cons.name)
    db.add(new_cons)
    db.commit()
    db.refresh(new_cons)
    return new_cons

@router.get("/reports/consultations/", response_model=List[ReportConsultationOut])
def get_report_consultations(db: Session = Depends(get_db)):
    return db.query(ReportConsultation).all()



# Assign collaborator to project
@router.post("/{project_id}/add-collaborator/{user_id}", response_model=ProjectOut)
def add_collaborator(project_id: str, user_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    user = db.query(ClientUser).filter(ClientUser.id == user_id).first()
    if not project or not user:
        raise HTTPException(404, "Project or User not found")
    if user not in project.collaborators:
        project.collaborators.append(user)
        db.commit()
        db.refresh(project)
    return project

# Remove collaborator from project
@router.delete("/{project_id}/remove-collaborator/{user_id}", response_model=ProjectOut)
def remove_collaborator(project_id: str, user_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    user = db.query(ClientUser).filter(ClientUser.id == user_id).first()
    if not project or not user:
        raise HTTPException(404, "Project or User not found")
    if user in project.collaborators:
        project.collaborators.remove(user)
        db.commit()
        db.refresh(project)
    return project
