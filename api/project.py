import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, Request, requests, status
from sqlalchemy.orm import Session
from typing import List
from api.deps import require_role
from models.ml_analysis_result import MLAnalysisResult
from models.project import MediaCategory, Project,ProjectCategory, ProjectThematicAreas, MediaSource, ReportAvenue, ReportTime, ReportConsultation
from models.client_user import ClientUser
from schemas.client import PaginatedResponse
from schemas.hamasa_user import UserRole
from schemas.project import *
from db import get_db
from utils.pagination import paginate_queryset

router = APIRouter(prefix="/projects", tags=["Projects"])

#--------------------------------------------------------------------------------------------------
# ---------------------------- Project CRUD Operations --------------------------------------------
#--------------------------------------------------------------------------------------------------

#---------------------
# Create a project
# ---------------------
@router.post("/", response_model=ProjectOut)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
    ]))
):

    new_project = Project(
        title=project.title,
        description=project.description,
        client_id=project.client_id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # ---------------------
    # Categories
    # ---------------------
    if project.category_ids:
        new_project.categories = db.query(ProjectCategory).filter(
            ProjectCategory.id.in_(project.category_ids)
        ).all()

    # ---------------------
    # Thematic Areas (NEW)
    # User submits "new" areas, not existing ones
    # ---------------------
    created_thematic_areas = []
    for ta in project.thematic_areas:
        new_area = ProjectThematicAreas(
            area=ta.area,
            title=ta.title,
            description=ta.description,
            monitoring_objective=ta.monitoring_objectives  # ARRAY → JSONB
        )
        db.add(new_area)
        created_thematic_areas.append(new_area)

    db.commit()
    for area in created_thematic_areas:
        db.refresh(area)
    
    new_project.thematic_areas.extend(created_thematic_areas)

    # ---------------------
    # Collaborators
    # ---------------------
    if project.collaborator_ids:
        new_project.collaborators = db.query(ClientUser).filter(
            ClientUser.id.in_(project.collaborator_ids)
        ).all()

    # ---------------------
    # Media sources
    # ---------------------
    if project.media_source_ids:
        new_project.media_sources = db.query(MediaSource).filter(
            MediaSource.id.in_(project.media_source_ids)
        ).all()

    # ---------------------
    # Report Avenues
    # ---------------------
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





#------------------------
# Read all projects
#------------------------
@router.get("/", response_model=PaginatedResponse)
def get_projects(
    request: Request,
    filters: ProjectFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ]))
):

    query = db.query(Project).filter(Project.is_deleted == False)

    if filters.title:
        query = query.filter(Project.title.ilike(f"%{filters.title}%"))

    if filters.client_id:
        query = query.filter(Project.client_id == filters.client_id)

    if filters.status:
        query = query.filter(Project.status == filters.status)

    # Sorting
    if filters.sort == "asc":
        query = query.order_by(Project.created_at.asc())
    else:
        query = query.order_by(Project.created_at.desc())

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectOut)




# --------------------------
# Update project
# --------------------------
@router.put("/{uid}/", response_model=ProjectOut)
def update_project(uid: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == uid, Project.is_deleted == False).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


# --------------------------
# Delete project
# --------------------------
@router.delete("/{uid}/", status_code=204)
def delete_project(uid: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == uid, Project.is_deleted == False).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_deleted = True
    db.commit()
    return




#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Category CRUD Operations ----------------------------------
#--------------------------------------------------------------------------------------------------

#----------------------------------------------
# Create Categories all admins and client admin
#----------------------------------------------
@router.post("/categories/", response_model=ProjectCategoryOut)
def create_category(
    category: ProjectCategoryCreate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db),
):
    # Check if category exists
    existing = db.query(ProjectCategory).filter(
        ProjectCategory.category.ilike(category.category)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Category already exists"
        )

    new_cat = ProjectCategory(
        category=category.category.strip(),
        description=category.description.strip()
    )

    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


#------------------------------
# get all categories
#------------------------------
@router.get("/categories/", response_model=PaginatedResponse)
def get_categories(
    request: Request,
    filters: CategoryFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ProjectCategory).filter(ProjectCategory.is_deleted == False)

    # Search filter
    if filters.search:
        query = query.filter(
            ProjectCategory.category.ilike(f"%{filters.search}%")
        )

    # Sorting
    sort_field = getattr(ProjectCategory, filters.sort_by, ProjectCategory.created_at)
    if filters.sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectCategoryOut)


#------------------------------
# get category by id
#------------------------------
@router.get("/categories/{category_id}", response_model=ProjectCategoryOut)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    return category



#------------------------------
# update category
#------------------------------
@router.patch("/categories/{category_id}", response_model=ProjectCategoryOut)
def update_category(
    category_id: uuid.UUID,
    data: ProjectCategoryUpdate,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db),
):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    # Prevent duplicates
    if data.category:
        exists = db.query(ProjectCategory).filter(
            ProjectCategory.category.ilike(data.category),
            ProjectCategory.id != category_id
        ).first()

        if exists:
            raise HTTPException(400, "Another category with that name already exists")

        category.category = data.category.strip()

    db.commit()
    db.refresh(category)
    return category



#------------------------------
# delete category
#------------------------------
@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db),
):
    category = db.query(ProjectCategory).filter(
        ProjectCategory.id == category_id,
        ProjectCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Category not found")

    category.is_deleted = True
    db.commit()
    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Thematic-Areas CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#----------------------------------------------
# create Thematic Areas all admins 
#----------------------------------------------
@router.post("/thematic-areas/", response_model=ProjectThematicAreaOut)
def create_thematic_area(
    area: ProjectThematicAreaCreate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Check duplicate
    existing = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.area.ilike(area.area)
    ).first()

    if existing:
        raise HTTPException(400, "Thematic area already exists")

    new_area = ProjectThematicAreas(
        area=area.area.strip(),
        title=area.title.strip(),
        description=area.description,
        monitoring_objective=area.monitoring_objective  # <-- list (JSONB)
    )

    db.add(new_area)
    db.commit()
    db.refresh(new_area)

    return new_area


#------------------------------
# get all thematic areas
#------------------------------
@router.get("/thematic-areas/", response_model=PaginatedResponse)
def get_thematic_areas(
    request: Request,
    filters: ThematicAreaFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ProjectThematicAreas).filter(ProjectThematicAreas.is_deleted == False)

    # Search across area, title, description
    if filters.search:
        search = f"%{filters.search}%"
        query = query.filter(
            ProjectThematicAreas.area.ilike(search) |
            ProjectThematicAreas.title.ilike(search) |
            ProjectThematicAreas.description.ilike(search)
        )

    # Sort
    sort_field = getattr(ProjectThematicAreas, filters.sort_by, ProjectThematicAreas.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, ProjectThematicAreaOut)


#------------------------------
# get thematic area by id
#------------------------------
@router.get("/thematic-areas/{id}", response_model=ProjectThematicAreaOut)
def get_thematic_area(id: uuid.UUID, db: Session = Depends(get_db)):
    area = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not area:
        raise HTTPException(404, "Thematic area not found")

    return area

#------------------------------
# update thematic area
#------------------------------
@router.patch("/thematic-areas/{id}", response_model=ProjectThematicAreaOut)
def update_thematic_area(
    id: uuid.UUID,
    data: ProjectThematicAreaUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    area = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not area:
        raise HTTPException(404, "Thematic area not found")

    # Prevent duplicate names
    if data.area:
        exists = db.query(ProjectThematicAreas).filter(
            ProjectThematicAreas.area.ilike(data.area),
            ProjectThematicAreas.id != id
        ).first()

        if exists:
            raise HTTPException(400, "Another thematic area with that name already exists")

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(area, field, value)

    db.commit()
    db.refresh(area)

    return area

#------------------------------
# delete thematic area
#------------------------------
@router.delete("/thematic-areas/{id}", status_code=204)
def delete_thematic_area(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    area = db.query(ProjectThematicAreas).filter(
        ProjectThematicAreas.id == id,
        ProjectThematicAreas.is_deleted == False
    ).first()

    if not area:
        raise HTTPException(404, "Thematic area not found")

    area.is_deleted = True
    db.commit()
    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Media-Category CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#------------------------------
# Media Create Categories
#------------------------------
@router.post("/media-categories/", response_model=MediaCategoryOut)
def create_media_category(
    category: MediaCategoryBase,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Prevent duplicates
    exists = db.query(MediaCategory).filter(
        MediaCategory.name.ilike(category.name)
    ).first()

    if exists:
        raise HTTPException(400, "Media category already exists")

    new_cat = MediaCategory(
        name=category.name.strip(),
        description=category.description
    )

    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    return new_cat


#------------------------------
# get all media categories
#------------------------------
@router.get("/media-categories/", response_model=PaginatedResponse)
def get_media_categories(
    request: Request,
    filters: MediaCategoryFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(MediaCategory).filter(MediaCategory.is_deleted == False)

    # Search by name or description
    if filters.search:
        search = f"%{filters.search}%"
        query = query.filter(
            MediaCategory.name.ilike(search) |
            MediaCategory.description.ilike(search)
        )

    # Sorting
    sort_field = getattr(MediaCategory, filters.sort_by, MediaCategory.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, MediaCategoryOut)


#------------------------------
# get media category by id
#------------------------------
@router.get("/media-categories/{id}", response_model=MediaCategoryOut)
def get_media_category(id: uuid.UUID, db: Session = Depends(get_db)):
    category = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    return category


#------------------------------
# update media category
#------------------------------
@router.patch("/media-categories/{id}", response_model=MediaCategoryOut)
def update_media_category(
    id: uuid.UUID,
    data: MediaCategoryUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    category = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    # Prevent duplicate category name
    if data.name:
        exists = db.query(MediaCategory).filter(
            MediaCategory.name.ilike(data.name),
            MediaCategory.id != id
        ).first()
        if exists:
            raise HTTPException(400, "Another category with that name already exists")

    # Apply updates
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return category


#------------------------------
# delete media category
#------------------------------
@router.delete("/media-categories/{id}", status_code=204)
def delete_media_category(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    category = db.query(MediaCategory).filter(
        MediaCategory.id == id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    category.is_deleted = True
    db.commit()

    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Media-Sources CRUD Operations ----------------------------------
#--------------------------------------------------------------------------------------------------


#-------------------
# Media Create Sources
#-------------------
@router.post("/media-sources/", response_model=MediaSourceOut)
def create_media_source(
    source: MediaSourceBase,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer,
        UserRole.data_clerk,
        UserRole.org_user
    ])),
    db: Session = Depends(get_db)
):
    # Ensure category exists
    category = db.query(MediaCategory).filter(
        MediaCategory.id == source.category_id,
        MediaCategory.is_deleted == False
    ).first()

    if not category:
        raise HTTPException(404, "Media category not found")

    # Prevent duplicate name inside the same category
    exists = db.query(MediaSource).filter(
        MediaSource.name.ilike(source.name),
        MediaSource.category_id == source.category_id,
        MediaSource.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Media source already exists in this category")

    new_source = MediaSource(
        name=source.name.strip(),
        category_id=source.category_id
    )

    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    return new_source

#------------------------------
# get all media sources
#------------------------------
@router.get("/media-sources/", response_model=PaginatedResponse)
def get_media_sources(
    request: Request,
    filters: MediaSourceFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(MediaSource).filter(MediaSource.is_deleted == False)

    # Filter by category
    if filters.category_id:
        query = query.filter(MediaSource.category_id == filters.category_id)

    # Search by name
    if filters.search:
        search = f"%{filters.search}%"
        query = query.filter(MediaSource.name.ilike(search))

    # Sorting
    sort_field = getattr(MediaSource, filters.sort_by, MediaSource.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order.lower() == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]

    return paginate_queryset(query, page, page_size, base_url, MediaSourceOut)


#------------------------------
# get media source by id
#------------------------------
@router.get("/media-sources/{id}", response_model=MediaSourceOut)
def get_media_source(id: uuid.UUID, db: Session = Depends(get_db)):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    return source

#------------------------------
# update media source
#------------------------------
@router.patch("/media-sources/{id}", response_model=MediaSourceOut)
def update_media_source(
    id: uuid.UUID,
    data: MediaSourceUpdate,
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.org_admin,
        UserRole.reviewer
    ])),
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    update_data = data.model_dump(exclude_unset=True)

    # If category is being changed, verify it exists
    if "category_id" in update_data:
        category = db.query(MediaCategory).filter(
            MediaCategory.id == update_data["category_id"],
            MediaCategory.is_deleted == False
        ).first()

        if not category:
            raise HTTPException(404, "New category not found")

    # Prevent duplicates inside the same category
    if "name" in update_data or "category_id" in update_data:
        name = update_data.get("name", source.name)
        category_id = update_data.get("category_id", source.category_id)

        exists = db.query(MediaSource).filter(
            MediaSource.name.ilike(name),
            MediaSource.category_id == category_id,
            MediaSource.id != id,
            MediaSource.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another source with that name already exists in this category")

    # Apply updates
    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)

    return source


#------------------------------
# delete media source
#------------------------------
@router.delete("/media-sources/{id}", status_code=204)
def delete_media_source(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    source = db.query(MediaSource).filter(
        MediaSource.id == id,
        MediaSource.is_deleted == False
    ).first()

    if not source:
        raise HTTPException(404, "Media source not found")

    source.is_deleted = True
    db.commit()
    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report-Avenues CRUD Operations -----------------------------
#--------------------------------------------------------------------------------------------------


#-------------------
# Report Avenues
#-------------------
@router.post("/report-avenues/", response_model=ReportAvenueOut)
def create_report_avenue(
    data: ReportAvenueCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    # Prevent duplicates
    exists = db.query(ReportAvenue).filter(
        ReportAvenue.name.ilike(data.name),
        ReportAvenue.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report avenue already exists")

    avenue = ReportAvenue(name=data.name.strip())
    db.add(avenue)
    db.commit()
    db.refresh(avenue)
    return avenue

#------------------------------
# get all report avenues
#------------------------------
@router.get("/report-avenues/", response_model=PaginatedResponse)
def list_report_avenues(
    request: Request,
    filters: ReportAvenueFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportAvenue).filter(ReportAvenue.is_deleted == False)

    if filters.search:
        query = query.filter(ReportAvenue.name.ilike(f"%{filters.search}%"))

    sort_field = getattr(ReportAvenue, filters.sort_by, ReportAvenue.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportAvenueOut)


#------------------------------
# Update report avenue
#------------------------------
@router.patch("/report-avenues/{id}", response_model=ReportAvenueOut)
def update_report_avenue(
    id: uuid.UUID,
    data: ReportAvenueUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    avenue = db.query(ReportAvenue).filter(
        ReportAvenue.id == id,
        ReportAvenue.is_deleted == False
    ).first()

    if not avenue:
        raise HTTPException(404, "Report avenue not found")

    # Check duplicate
    if data.name:
        exists = db.query(ReportAvenue).filter(
            ReportAvenue.name.ilike(data.name),
            ReportAvenue.id != id,
            ReportAvenue.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another avenue already exists with this name")

    if data.name:
        avenue.name = data.name

    db.commit()
    db.refresh(avenue)
    return avenue


#------------------------------
# Delete report avenue
#------------------------------
@router.delete("/report-avenues/{id}", status_code=204)
def delete_report_avenue(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    avenue = db.query(ReportAvenue).filter(
        ReportAvenue.id == id,
        ReportAvenue.is_deleted == False
    ).first()

    if not avenue:
        raise HTTPException(404, "Report avenue not found")

    avenue.is_deleted = True
    db.commit()
    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report_Times CRUD Operations -------------------------------
#--------------------------------------------------------------------------------------------------

#-------------------
# Report Times
#-------------------
@router.post("/report-times/", response_model=ReportTimeOut)
def create_report_time(
    data: ReportTimeCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    exists = db.query(ReportTime).filter(
        ReportTime.name.ilike(data.name),
        ReportTime.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report time already exists")

    new_time = ReportTime(name=data.name.strip())
    db.add(new_time)
    db.commit()
    db.refresh(new_time)
    return new_time


#------------------------------
# get all report times
#------------------------------
@router.get("/report-times/", response_model=PaginatedResponse)
def list_report_times(
    request: Request,
    filters: ReportTimeFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportTime).filter(ReportTime.is_deleted == False)

    if filters.search:
        query = query.filter(ReportTime.name.ilike(f"%{filters.search}%"))

    sort_field = getattr(ReportTime, filters.sort_by, ReportTime.created_at)
    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportTimeOut)

#------------------------------
# Update report time
#------------------------------
@router.patch("/report-times/{id}", response_model=ReportTimeOut)
def update_report_time(
    id: uuid.UUID,
    data: ReportTimeUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rtime = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not rtime:
        raise HTTPException(404, "Report time not found")

    if data.name:
        exists = db.query(ReportTime).filter(
            ReportTime.name.ilike(data.name),
            ReportTime.id != id,
            ReportTime.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "Another report time already exists with this name")

        rtime.name = data.name

    db.commit()
    db.refresh(rtime)
    return rtime


#------------------------------
# Delete report time
#------------------------------
@router.delete("/report-times/{id}", status_code=204)
def delete_report_time(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rtime = db.query(ReportTime).filter(
        ReportTime.id == id,
        ReportTime.is_deleted == False
    ).first()

    if not rtime:
        raise HTTPException(404, "Report time not found")

    rtime.is_deleted = True
    db.commit()
    return



#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Report-Consultations CRUD Operations -----------------------
#--------------------------------------------------------------------------------------------------


#-------------------------
# Report Consultations
#-------------------------
@router.post("/report-consultations/", response_model=ReportConsultationOut)
def create_report_consultation(
    data: ReportConsultationCreate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    exists = db.query(ReportConsultation).filter(
        ReportConsultation.name.ilike(data.name),
        ReportConsultation.is_deleted == False
    ).first()

    if exists:
        raise HTTPException(400, "Report consultation already exists")

    rc = ReportConsultation(name=data.name.strip())
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc

#------------------------------
# get all report consultations
#------------------------------
@router.get("/report-consultations/", response_model=PaginatedResponse)
def list_report_consultations(
    request: Request,
    filters: ReportConsultationFilters = Depends(),
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    query = db.query(ReportConsultation).filter(ReportConsultation.is_deleted == False)

    if filters.search:
        query = query.filter(ReportConsultation.name.ilike(f"%{filters.search}%"))

    sort_field = getattr(ReportConsultation, filters.sort_by, ReportConsultation.created_at)

    query = query.order_by(
        sort_field.asc() if filters.sort_order == "asc" else sort_field.desc()
    )

    base_url = str(request.url).split("?")[0]
    return paginate_queryset(query, page, page_size, base_url, ReportConsultationOut)


#------------------------------
# Update report consultation
#------------------------------
@router.patch("/report-consultations/{id}", response_model=ReportConsultationOut)
def update_report_consultation(
    id: uuid.UUID,
    data: ReportConsultationUpdate,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rc = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not rc:
        raise HTTPException(404, "Report consultation not found")

    if data.name:
        exists = db.query(ReportConsultation).filter(
            ReportConsultation.name.ilike(data.name),
            ReportConsultation.id != id,
            ReportConsultation.is_deleted == False
        ).first()

        if exists:
            raise HTTPException(400, "A consultation type with that name already exists")

        rc.name = data.name

    db.commit()
    db.refresh(rc)
    return rc

#------------------------------
# Delete report consultation
#------------------------------
@router.delete("/report-consultations/{id}", status_code=204)
def delete_report_consultation(
    id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin])),
    db: Session = Depends(get_db)
):
    rc = db.query(ReportConsultation).filter(
        ReportConsultation.id == id,
        ReportConsultation.is_deleted == False
    ).first()

    if not rc:
        raise HTTPException(404, "Report consultation not found")

    rc.is_deleted = True
    db.commit()
    return


#--------------------------------------------------------------------------------------------------
# ---------------------------- Project-Collaborator CRUD Operations -------------------------------
#--------------------------------------------------------------------------------------------------


#--------------------------------
# Assign collaborator to project
#--------------------------------
@router.post("/{project_id}/collaborators/{user_id}", response_model=ProjectOut)
def add_collaborator(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Fetch user
    user = db.query(ClientUser).filter(
        ClientUser.id == user_id,
        ClientUser.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Org Admins can only modify collaborators for their own client
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(project.client_id):
            raise HTTPException(403, "You cannot modify another organisation's project")
        if str(user.client_id) != str(project.client_id):
            raise HTTPException(403, "Collaborator does not belong to your organisation")

    # Prevent duplicates
    if user in project.collaborators:
        raise HTTPException(400, "Collaborator already assigned to this project")

    # Add collaborator
    project.collaborators.append(user)
    db.commit()
    db.refresh(project)

    return project


#--------------------------------
# Remove collaborator from project
#--------------------------------
@router.delete("/{project_id}/collaborators/{user_id}", response_model=ProjectOut)
def remove_collaborator(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user=Depends(require_role([UserRole.super_admin, UserRole.org_admin])),
    db: Session = Depends(get_db)
):
    # Fetch project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.is_deleted == False
    ).first()

    if not project:
        raise HTTPException(404, "Project not found")

    # Fetch user
    user = db.query(ClientUser).filter(
        ClientUser.id == user_id,
        ClientUser.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Org Admins can only update users within their org
    if current_user["role"] == UserRole.org_admin:
        if str(current_user["client_id"]) != str(project.client_id):
            raise HTTPException(403, "You cannot modify another organisation's project")
        if str(user.client_id) != str(project.client_id):
            raise HTTPException(403, "User does not belong to your organisation")

    # Check assignment before removing
    if user not in project.collaborators:
        raise HTTPException(400, "Collaborator is not assigned to this project")

    project.collaborators.remove(user)
    db.commit()
    db.refresh(project)

    return project










#-----------------------------------
# Get Project Details Needed for ML
#-----------------------------------
@router.get("/{uid}/ml-details/", response_model=ProjectMLDetailsOut)
def get_project_ml_details(
    uid: UUID4,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
    ]))
):
    project = db.query(Project).filter(Project.id == uid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectMLDetailsOut(
        id=project.id,
        title=project.title,
        thematic_areas=[ta.area for ta in project.thematic_areas],
        media_sources=[ms.name for ms in project.media_sources],
    )


# -----------------------------------
# Project ML Analysis Results
# -----------------------------------
@router.post("/ml-csv-url", response_model=MLCSVStoredResponse,
             dependencies=[Depends(require_role([
                 UserRole.super_admin,
                 UserRole.reviewer,
             ]))])
def process_ml_csv(
    payload: MLCSVRequest,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.uid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Download CSV
    try:
        response = requests.get(payload.csv_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download CSV: {e}")

    # 2. Parse CSV
    csv_text = response.text
    reader = csv.DictReader(StringIO(csv_text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty")

    # 3. Clear previous ML results for this project
    db.query(MLAnalysisResult).filter(
        MLAnalysisResult.uid == project.id
    ).delete()

    # 4. Insert results
    for i, row in enumerate(rows):
        ml_row = MLAnalysisResult(
            uid=project.id,
            row_number=i + 1,
            data=row
        )
        db.add(ml_row)

    db.commit()

    return MLCSVStoredResponse(
        uid=project.id,
        total_rows=len(rows),
    )


# -----------------------------------
# Get Project ML Analysis Results
# -----------------------------------
@router.get("/{uid}/ml-results")
def get_ml_results(
    uid: UUID4,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([
        UserRole.super_admin,
        UserRole.reviewer,
    ]))
):
    results = (
        db.query(MLAnalysisResult)
        .filter(MLAnalysisResult.uid == uid)
        .order_by(MLAnalysisResult.row_number)
        .all()
    )

    return [r.data for r in results]
