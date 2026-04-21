import os
import uuid
import tempfile
import threading
import PIL
import numpy as np
import streamlit as st
import mediapipe as mp
import cv2
import json
import traceback
import logging
from pathlib import Path
from sklearn.neighbors import KNeighborsClassifier
from sqlmodel import Session, select
from pages.helper import db_queries
from pages.helper.data_models import PublicSubmissions

# ============================================================================
# LOGGING & WARNINGS SUPPRESSION
# ============================================================================
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*sparse_softmax_cross_entropy.*')


# ============================================================================
# SINGLETON MODEL CACHE
# ============================================================================
class DeepFaceModelCache:
    _instance = None
    _lock = threading.Lock()
    _models = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_model(cls, model_name: str = "Facenet512"):
        instance = cls()
        if model_name not in instance._models:
            with cls._lock:
                if model_name not in instance._models:
                    try:
                        from deepface import DeepFace
                        logger.info(f"🔄 Loading {model_name} model (first time)...")
                        instance._models[model_name] = DeepFace.build_model(model_name)
                        logger.info(f"✅ {model_name} cached successfully")
                    except Exception as e:
                        logger.error(f"❌ Failed to load {model_name}: {str(e)}")
                        return None
        return instance._models[model_name]

    @classmethod
    def preload_models(cls, model_names: list = None):
        if model_names is None:
            model_names = ["Facenet512", "Facenet", "VGG-Face"]
        logger.info(f"🚀 Preloading {len(model_names)} models...")
        for model_name in model_names:
            cls.get_model(model_name)
        logger.info("✅ All models preloaded!")

    @classmethod
    def clear_cache(cls):
        instance = cls()
        instance._models.clear()
        logger.info("🗑️ Model cache cleared")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def image_obj_to_numpy(image_obj) -> np.ndarray:
    image = PIL.Image.open(image_obj)
    image = image.convert("RGB")
    return np.array(image)


def _to_rgb_image(image: np.ndarray) -> np.ndarray:
    image = np.array(image)
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    elif image.shape[-1] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
    return image


def _detect_and_crop_primary_face(image_rgb: np.ndarray) -> np.ndarray | None:
    h, w = image_rgb.shape[:2]
    mp_face_detection = mp.solutions.face_detection

    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.35) as face_detector:
        results = face_detector.process(image_rgb)
        if not results.detections:
            return None

        det = max(
            results.detections,
            key=lambda d: d.score[0] if getattr(d, "score", None) else 0.0,
        )
        rel = det.location_data.relative_bounding_box
        x1 = int(rel.xmin * w)
        y1 = int(rel.ymin * h)
        bw = int(rel.width * w)
        bh = int(rel.height * h)

        mx = int(0.25 * bw)
        my = int(0.25 * bh)

        x1 = max(0, x1 - mx)
        y1 = max(0, y1 - my)
        x2 = min(w, x1 + bw + 2 * mx)
        y2 = min(h, y1 + bh + 2 * my)

        if x2 <= x1 or y2 <= y1:
            return None
        return image_rgb[y1:y2, x1:x2]


def extract_face_mesh_landmarks(image: np.ndarray):
    image = _to_rgb_image(image)

    candidates = [image]
    face_crop = _detect_and_crop_primary_face(image)
    if face_crop is not None and face_crop.size > 0:
        candidates.extend(
            [
                face_crop,
                cv2.resize(face_crop, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC),
                cv2.resize(face_crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC),
            ]
        )

    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.35,
        min_tracking_confidence=0.35,
    ) as face_mesh:
        for candidate in candidates:
            results = face_mesh.process(candidate)
            if not results.multi_face_landmarks:
                continue

            landmarks = results.multi_face_landmarks[0].landmark
            face_mesh_points = [coord for lm in landmarks for coord in (lm.x, lm.y, lm.z)]
            if len(face_mesh_points) == 1404:
                return face_mesh_points

    st.error("Couldn't find face mesh in image. Please try another image.")
    return None


def extract_face_embedding(image: np.ndarray, model_name: str = "Facenet512"):
    try:
        from deepface import DeepFace

        img = _to_rgb_image(image)
        face_crop = _detect_and_crop_primary_face(img)
        preferred_img = face_crop if face_crop is not None and face_crop.size > 0 else img
        bgr_image = cv2.cvtColor(preferred_img, cv2.COLOR_RGB2BGR)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4()}.jpg")
            cv2.imwrite(tmp_path, bgr_image)

            model_order = list(dict.fromkeys([model_name, "Facenet", "VGG-Face"]))
            attempts = [
                {"enforce_detection": True,  "detector_backend": "opencv",     "attempt": "strict_opencv"},
                {"enforce_detection": False, "detector_backend": "opencv",     "attempt": "relaxed_opencv"},
                {"enforce_detection": False, "detector_backend": "retinaface", "attempt": "relaxed_retinaface"},
            ]

            last_error = "unknown"

            for model in model_order:
                for cfg in attempts:
                    try:
                        representation = DeepFace.represent(
                            img_path=tmp_path,
                            model_name=model,
                            enforce_detection=cfg["enforce_detection"],
                            detector_backend=cfg["detector_backend"],
                        )

                        if isinstance(representation, list) and representation and "embedding" in representation[0]:
                            embedding = representation[0]["embedding"]
                        elif isinstance(representation, dict) and "embedding" in representation:
                            embedding = representation["embedding"]
                        else:
                            embedding = None

                        if embedding is not None:
                            return {
                                "status": "success",
                                "embedding": embedding,
                                "embedding_model": model,
                                "embedding_dim": len(embedding),
                                "detector_backend": cfg["detector_backend"],
                                "attempt": cfg["attempt"],
                            }
                    except Exception as inner_err:
                        last_error = f"{model}/{cfg['attempt']}: {str(inner_err)}"
                        continue

            return {"status": "failed", "embedding": None, "error": last_error}

    except Exception as e:
        return {
            "status": "failed",
            "embedding": None,
            "error": str(e),
            "trace": traceback.format_exc()[:500],
        }


# ============================================================================
# DUPLICATE DETECTION — PUBLIC vs PUBLIC
# ============================================================================

def normalize_name(name: str) -> str:
    return name.strip().lower() if name else ""


def _cosine_distance(v1, v2) -> float:
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 1.0
    return 1.0 - float(np.dot(a, b) / denom)


def check_duplicate_public_case(
    face_mesh,
    name,
    face_embedding=None,
    embedding_model: str = "",
    embedding_threshold: float = 0.35,
    mesh_threshold: float = 3.0,
):
    """
    Check if a public submission already exists for this face.
    1) Primary: embedding cosine distance
    2) Fallback: face-mesh KNN distance
    """
    try:
        input_name = normalize_name(name)

        # ---------- PRIMARY: Embedding cosine similarity ----------
        if face_embedding and embedding_model:
            try:
                with Session(db_queries.engine) as session:
                    embed_rows = session.exec(
                        select(
                            PublicSubmissions.id,
                            PublicSubmissions.face_embedding,
                            PublicSubmissions.embedding_model,
                        ).where(PublicSubmissions.status == "NF")
                    ).all()

                best_embed_match = None
                best_embed_distance = None

                for case_id, case_embedding_str, case_model in embed_rows:
                    if not case_embedding_str or case_embedding_str in ["", "null"]:
                        continue
                    if (case_model or "") != embedding_model:
                        continue
                    try:
                        case_embedding = json.loads(case_embedding_str)
                        if not isinstance(case_embedding, list):
                            continue
                        if len(case_embedding) != len(face_embedding):
                            continue
                        dist = _cosine_distance(face_embedding, case_embedding)
                        if best_embed_distance is None or dist < best_embed_distance:
                            best_embed_distance = dist
                            best_embed_match = case_id
                    except Exception:
                        continue

                if (best_embed_match is not None and
                        best_embed_distance is not None and
                        best_embed_distance <= embedding_threshold):
                    case_detail = db_queries.get_public_case_detail(best_embed_match)
                    matched_name = normalize_name(str(case_detail[0][1])) if case_detail else ""
                    return {
                        "match": True,
                        "matched_id": best_embed_match,
                        "distance": float(best_embed_distance),
                        "name_match": bool(input_name and matched_name and input_name == matched_name),
                        "matching_strategy": "embedding_cosine",
                    }
            except Exception as e:
                logger.warning(f"Embedding matching failed: {str(e)}")

        # ---------- FALLBACK: Face mesh KNN ----------
        public_cases = db_queries.fetch_public_cases(train_data=True, status="NF")

        if not public_cases or len(public_cases) == 0:
            return {"match": False}

        labels, features, names = [], [], []

        for case in public_cases:
            case_id, case_face_mesh = case
            if not case_face_mesh or case_face_mesh in ["", "null"]:
                continue
            try:
                mesh = json.loads(case_face_mesh)
                if len(mesh) != 1404:
                    continue
                labels.append(case_id)
                features.append(mesh)
                case_detail = db_queries.get_public_case_detail(case_id)
                case_name = str(case_detail[0][1]) if case_detail else ""
                names.append(normalize_name(case_name))
            except Exception:
                continue

        if len(features) == 0:
            return {"match": False}

        knn = KNeighborsClassifier(n_neighbors=1, algorithm="ball_tree")
        knn.fit(features, list(range(len(features))))

        distance = knn.kneighbors([face_mesh])[0][0][0]

        if distance <= mesh_threshold:
            idx = knn.predict([face_mesh])[0]
            matched_id = labels[idx]
            matched_name = names[idx]
            name_match = input_name == matched_name if input_name and matched_name else False
            return {
                "match": True,
                "matched_id": matched_id,
                "distance": float(distance),
                "name_match": name_match,
                "matching_strategy": "mesh_knn_fallback",
            }

        return {"match": False}

    except Exception as e:
        logger.error(f"Duplicate check error: {str(e)}")
        return {"match": False, "error": str(e)}


# ============================================================================
# 🔥 NEW: CHECK FACE AGAINST REGISTERED (ADMIN) CASES
# ============================================================================

def check_against_registered_cases(
    face_mesh,
    face_embedding=None,
    embedding_model=None,
    embedding_threshold: float = 0.40,
    mesh_threshold: float = 3.0,
):
    """
    Check if uploaded face matches any admin-registered missing case.

    Used in the public portal to detect when someone uploads a photo of a
    person who is already registered as missing — blocks re-submission and
    shows existing case details instead.

    Returns:
        {"match": False}  — no registered case found
        {"match": True, "case": {...}}  — matched case details
    """
    try:
        from pages.helper.data_models import RegisteredCases

        # ── Step 1: Embedding cosine match (preferred) ──
        if face_embedding and embedding_model:
            with Session(db_queries.engine) as session:
                reg_cases = session.exec(
                    select(RegisteredCases).where(RegisteredCases.status == "NF")
                ).all()

            best_match = None
            best_dist = None

            for case in reg_cases:
                if not case.face_embedding or case.face_embedding in ["", "null"]:
                    continue
                if (case.embedding_model or "") != embedding_model:
                    continue
                try:
                    reg_emb = json.loads(case.face_embedding)
                    if not isinstance(reg_emb, list) or len(reg_emb) != len(face_embedding):
                        continue
                    dist = _cosine_distance(face_embedding, reg_emb)
                    if best_dist is None or dist < best_dist:
                        best_dist = dist
                        best_match = case
                except Exception:
                    continue

            if best_match is not None and best_dist is not None and best_dist <= embedding_threshold:
                return {
                    "match": True,
                    "method": "embedding",
                    "distance": best_dist,
                    "case": {
                        "id": best_match.id,
                        "name": best_match.name,
                        "age": best_match.age,
                        "last_seen": best_match.last_seen,
                        "contact": best_match.complainant_mobile,
                        "complainant": best_match.complainant_name,
                        "birth_marks": best_match.birth_marks,
                        "address": best_match.address,
                    }
                }

        # ── Step 2: Face mesh KNN fallback ──
        if face_mesh and len(face_mesh) == 1404:
            with Session(db_queries.engine) as session:
                reg_cases = session.exec(
                    select(RegisteredCases).where(RegisteredCases.status == "NF")
                ).all()

            valid_cases, valid_meshes = [], []

            for case in reg_cases:
                if not case.face_mesh or case.face_mesh in ["", "null"]:
                    continue
                try:
                    mesh = json.loads(case.face_mesh)
                    if isinstance(mesh, list) and len(mesh) == 1404:
                        valid_cases.append(case)
                        valid_meshes.append(mesh)
                except Exception:
                    continue

            if len(valid_cases) == 0:
                return {"match": False}

            X = np.array(valid_meshes, dtype=float)
            y = list(range(len(valid_cases)))

            knn = KNeighborsClassifier(n_neighbors=1, algorithm="ball_tree", weights="distance")
            knn.fit(X, y)

            query = np.array(face_mesh, dtype=float).reshape(1, -1)
            dist, idx = knn.kneighbors(query)
            closest_dist = float(dist[0][0])
            closest_idx = int(idx[0][0])

            if closest_dist <= mesh_threshold:
                matched_case = valid_cases[closest_idx]
                return {
                    "match": True,
                    "method": "face_mesh",
                    "distance": closest_dist,
                    "case": {
                        "id": matched_case.id,
                        "name": matched_case.name,
                        "age": matched_case.age,
                        "last_seen": matched_case.last_seen,
                        "contact": matched_case.complainant_mobile,
                        "complainant": matched_case.complainant_name,
                        "birth_marks": matched_case.birth_marks,
                        "address": matched_case.address,
                    }
                }

        return {"match": False}

    except Exception as e:
        logger.error(f"check_against_registered_cases error: {str(e)}")
        return {"match": False}