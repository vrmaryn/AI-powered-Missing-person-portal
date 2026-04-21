# import os
# import pickle
# import json
# import traceback
# import warnings
# from collections import defaultdict

# import pandas as pd
# import numpy as np


# warnings.filterwarnings(action="ignore")


# from pages.helper import db_queries


# def get_public_cases_data(status="NF"):
#     try:
#         result = db_queries.fetch_public_cases(train_data=True, status=status)
#         d1 = pd.DataFrame(result, columns=["label", "face_mesh"])
#         d1["face_mesh"] = d1["face_mesh"].apply(lambda x: json.loads(x))
#         d2 = pd.DataFrame(d1.pop("face_mesh").values.tolist(), index=d1.index).rename(
#             columns=lambda x: "fm_{}".format(x + 1)
#         )
#         df = d1.join(d2)
#         # Ensure all columns except label are float
#         for col in df.columns:
#             if col != "label":
#                 df[col] = pd.to_numeric(df[col], errors="coerce")
#         return df

#     except Exception as e:
#         traceback.print_exc()
#         return None


# def get_registered_cases_data(status="NF"):
#     try:
#         from pages.helper.db_queries import engine, RegisteredCases
#         import pandas as pd
#         import json
#         from sqlmodel import Session, select

#         with Session(engine) as session:
#             result = session.exec(
#                 select(
#                     RegisteredCases.id,
#                     RegisteredCases.face_mesh,
#                     RegisteredCases.status,
#                 )
#             ).all()
#             d1 = pd.DataFrame(result, columns=["label", "face_mesh", "status"])
#             if status:
#                 d1 = d1[d1["status"] == status]
#             d1["face_mesh"] = d1["face_mesh"].apply(lambda x: json.loads(x))
#             d2 = pd.DataFrame(
#                 d1.pop("face_mesh").values.tolist(), index=d1.index
#             ).rename(columns=lambda x: "fm_{}".format(x + 1))
#             df = d1.join(d2)
#             # Ensure all columns except label and status are float
#             for col in df.columns:
#                 if col not in ["label", "status"]:
#                     df[col] = pd.to_numeric(df[col], errors="coerce")
#             return df
#     except Exception as e:
#         traceback.print_exc()
#         return None


# from sklearn.neighbors import KNeighborsClassifier
# from sklearn.preprocessing import LabelEncoder


# def match(distance_threshold=3):
#     matched_images = defaultdict(list)
#     public_cases_df = get_public_cases_data()
#     registered_cases_df = get_registered_cases_data()

#     if public_cases_df is None or registered_cases_df is None:
#         return {"status": False, "message": "Couldn't connect to database"}
#     if len(public_cases_df) == 0 or len(registered_cases_df) == 0:
#         return {"status": False, "message": "No public or registered cases found"}

#     # Store original labels before encoding
#     original_reg_labels = registered_cases_df.iloc[:, 0].tolist()
#     original_pub_labels = public_cases_df.iloc[:, 0].tolist()

#     # Prepare training data - use index positions as labels for the classifier
#     reg_features = registered_cases_df.iloc[:, 2:].values.astype(float)

#     # Create simple numeric labels for KNN (0, 1, 2, ...)
#     numeric_labels = list(range(len(reg_features)))

#     # Train KNN classifier with numeric labels
#     knn = KNeighborsClassifier(n_neighbors=1, algorithm="ball_tree", weights="distance")
#     knn.fit(reg_features, numeric_labels)

#     # For each public submission, find the closest registered case
#     for i, row in public_cases_df.iterrows():
#         pub_label = original_pub_labels[i]  # Original public case ID
#         face_encoding = np.array(row[1:]).astype(float)

#         try:
#             # Get distances to nearest neighbors
#             closest_distances = knn.kneighbors([face_encoding])[0][0]
#             closest_distance = np.min(closest_distances)
#             print(f"Distance for case {pub_label}: {closest_distance}")

#             # FIXED: Changed >= to <= (lower distance = better match)
#             # Distance of 0.0 = perfect match, should be ACCEPTED
#             # Distance of 5.0 = poor match, should be REJECTED
#             if closest_distance <= distance_threshold:  # ✅ CORRECT LOGIC
#                 # Get the index of the predicted registered case
#                 predicted_idx = knn.predict([face_encoding])[0]
#                 # Get the original UUID of the registered case
#                 reg_label = original_reg_labels[predicted_idx]
#                 # Store the match
#                 matched_images[reg_label].append(pub_label)
#                 print(f"✅ MATCH FOUND: Public case {pub_label} matches Registered case {reg_label}")
#         except Exception as e:
#             print(f"Error processing public case {pub_label}: {str(e)}")
#             continue

#     return {"status": True, "result": matched_images}


# if __name__ == "__main__":
#     result = match()
#     print(result)


import os
import pickle
import json
import traceback
import warnings
import logging
from collections import defaultdict

import pandas as pd
import numpy as np


warnings.filterwarnings(action="ignore")

# Setup logging to file instead of console to avoid Windows handle issues
logging.basicConfig(
    filename='matching_errors.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


from pages.helper import db_queries


def get_public_cases_data(status="NF"):
    try:
        result = db_queries.fetch_public_cases(train_data=True, status=status)
        d1 = pd.DataFrame(result, columns=["label", "face_mesh"])

        # Remove empty values
        d1 = d1[d1["face_mesh"].notna()]
        d1 = d1[d1["face_mesh"] != "null"]
        d1 = d1[d1["face_mesh"] != ""]

        if len(d1) == 0:
            return None

        # Parse JSON safely
        d1["face_mesh"] = d1["face_mesh"].apply(
            lambda x: json.loads(x) if x else None
        )

        # Remove invalid JSON rows
        d1 = d1[d1["face_mesh"].notna()]

        # 🚨 Keep only correct length meshes (1404)
        d1 = d1[d1["face_mesh"].apply(lambda x: len(x) == 1404)]

        if len(d1) == 0:
            return None

        d2 = pd.DataFrame(
            d1.pop("face_mesh").values.tolist(),
            index=d1.index
        ).rename(columns=lambda x: f"fm_{x+1}")

        df = d1.join(d2).reset_index(drop=True)

        # Convert to float
        for col in df.columns:
            if col != "label":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 🚨 Drop any NaN rows
        df = df.dropna()

        if len(df) == 0:
            return None

        return df

    except Exception as e:
        logging.error(traceback.format_exc())
        return None

def get_registered_cases_data(status="NF"):
    try:
        from pages.helper.db_queries import engine, RegisteredCases
        from sqlmodel import Session, select

        with Session(engine) as session:
            result = session.exec(
                select(
                    RegisteredCases.id,
                    RegisteredCases.face_mesh,
                    RegisteredCases.status,
                )
            ).all()

        d1 = pd.DataFrame(result, columns=["label", "face_mesh", "status"])

        if status:
            d1 = d1[d1["status"] == status]

        d1 = d1[d1["face_mesh"].notna()]
        d1 = d1[d1["face_mesh"] != "null"]
        d1 = d1[d1["face_mesh"] != ""]

        if len(d1) == 0:
            return None

        d1["face_mesh"] = d1["face_mesh"].apply(
            lambda x: json.loads(x) if x else None
        )

        d1 = d1[d1["face_mesh"].notna()]

        # 🚨 Keep only correct length meshes
        d1 = d1[d1["face_mesh"].apply(lambda x: len(x) == 1404)]

        if len(d1) == 0:
            return None

        d2 = pd.DataFrame(
            d1.pop("face_mesh").values.tolist(),
            index=d1.index
        ).rename(columns=lambda x: f"fm_{x+1}")

        df = d1.join(d2).reset_index(drop=True)

        for col in df.columns:
            if col not in ["label", "status"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 🚨 Drop NaN rows
        df = df.dropna()

        if len(df) == 0:
            return None

        return df

    except Exception as e:
        logging.error(traceback.format_exc())
        return None

def get_public_embedding_data(status="NF"):
    try:
        from pages.helper.db_queries import engine
        from pages.helper.data_models import PublicSubmissions
        from sqlmodel import Session, select

        with Session(engine) as session:
            result = session.exec(
                select(
                    PublicSubmissions.id,
                    PublicSubmissions.face_embedding,
                    PublicSubmissions.embedding_model,
                    PublicSubmissions.status,
                )
            ).all()

        df = pd.DataFrame(result, columns=["label", "face_embedding", "embedding_model", "status"])
        if status:
            df = df[df["status"] == status]
        df = df[df["face_embedding"].notna()]
        df = df[df["face_embedding"] != ""]
        df = df[df["face_embedding"] != "null"]

        if len(df) == 0:
            return None

        df["face_embedding"] = df["face_embedding"].apply(lambda x: json.loads(x) if x else None)
        df = df[df["face_embedding"].notna()]
        df = df[df["face_embedding"].apply(lambda x: isinstance(x, list) and len(x) > 0)]
        if len(df) == 0:
            return None
        return df.reset_index(drop=True)
    except Exception:
        logging.error(traceback.format_exc())
        return None


def get_registered_embedding_data(status="NF"):
    try:
        from pages.helper.db_queries import engine
        from pages.helper.data_models import RegisteredCases
        from sqlmodel import Session, select

        with Session(engine) as session:
            result = session.exec(
                select(
                    RegisteredCases.id,
                    RegisteredCases.face_embedding,
                    RegisteredCases.embedding_model,
                    RegisteredCases.status,
                )
            ).all()

        df = pd.DataFrame(result, columns=["label", "face_embedding", "embedding_model", "status"])
        if status:
            df = df[df["status"] == status]
        df = df[df["face_embedding"].notna()]
        df = df[df["face_embedding"] != ""]
        df = df[df["face_embedding"] != "null"]

        if len(df) == 0:
            return None

        df["face_embedding"] = df["face_embedding"].apply(lambda x: json.loads(x) if x else None)
        df = df[df["face_embedding"].notna()]
        df = df[df["face_embedding"].apply(lambda x: isinstance(x, list) and len(x) > 0)]
        if len(df) == 0:
            return None
        return df.reset_index(drop=True)
    except Exception:
        logging.error(traceback.format_exc())
        return None


from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder


def _cosine_distance(v1, v2):
    a = np.array(v1, dtype=float)
    b = np.array(v2, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 1.0
    return 1.0 - float(np.dot(a, b) / denom)


def match(distance_threshold=3, embedding_threshold=0.35):
    matched_images = defaultdict(list)
    public_cases_df = get_public_cases_data()
    registered_cases_df = get_registered_cases_data()
    public_embed_df = get_public_embedding_data()
    registered_embed_df = get_registered_embedding_data()

    mesh_available = public_cases_df is not None and registered_cases_df is not None and len(public_cases_df) > 0 and len(registered_cases_df) > 0
    emb_available = public_embed_df is not None and registered_embed_df is not None and len(public_embed_df) > 0 and len(registered_embed_df) > 0

    if not mesh_available and not emb_available:
        return {"status": False, "message": "No valid embedding or face mesh data found"}

    matched_pub_ids = set()

    # ---------- Primary: Embedding cosine similarity ----------
    if emb_available:
        for _, pub_row in public_embed_df.iterrows():
            pub_label = pub_row["label"]
            pub_model = pub_row["embedding_model"] or ""
            pub_embedding = pub_row["face_embedding"]
            if not pub_model or not isinstance(pub_embedding, list):
                continue

            reg_model_df = registered_embed_df[registered_embed_df["embedding_model"] == pub_model]
            if len(reg_model_df) == 0:
                continue

            best_reg_label = None
            best_dist = None
            for _, reg_row in reg_model_df.iterrows():
                reg_embedding = reg_row["face_embedding"]
                if not isinstance(reg_embedding, list):
                    continue
                if len(reg_embedding) != len(pub_embedding):
                    continue
                dist = _cosine_distance(pub_embedding, reg_embedding)
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_reg_label = reg_row["label"]

            if best_reg_label is not None and best_dist is not None and best_dist <= embedding_threshold:
                matched_images[best_reg_label].append(pub_label)
                matched_pub_ids.add(pub_label)
                logging.info(
                    f"EMBED MATCH: Public case {pub_label} -> Registered case {best_reg_label} (cosine distance: {best_dist})"
                )

    # ---------- Fallback: existing mesh KNN ----------
    if not mesh_available:
        logging.info("Mesh fallback skipped: valid mesh data not available")
        return {"status": True, "result": matched_images}

    original_reg_labels = registered_cases_df["label"].tolist()
    original_pub_labels = public_cases_df["label"].tolist()
    logging.info(f"Processing mesh fallback with {len(original_reg_labels)} registered and {len(original_pub_labels)} public cases")

    # Prepare training data - skip label and status columns
    # Get column positions dynamically
    if "status" in registered_cases_df.columns:
        # Skip first 2 columns (label, status)
        reg_features = registered_cases_df.iloc[:, 2:].values.astype(float)
    else:
        # Skip first column (label)
        reg_features = registered_cases_df.iloc[:, 1:].values.astype(float)

    # Create simple numeric labels for KNN (0, 1, 2, ...)
    numeric_labels = list(range(len(reg_features)))

    # Train KNN classifier with numeric labels
    knn = KNeighborsClassifier(n_neighbors=1, algorithm="ball_tree", weights="distance")
    knn.fit(reg_features, numeric_labels)

    # For each public submission, find the closest registered case
    for idx, (_, row) in enumerate(public_cases_df.iterrows()):
        pub_label = original_pub_labels[idx]
        if pub_label in matched_pub_ids:
            continue

        # Get face encoding (skip label column)
        face_encoding = np.array(row[1:]).astype(float)

        try:
            # Get distances to nearest neighbors
            closest_distances = knn.kneighbors([face_encoding])[0][0]
            closest_distance = np.min(closest_distances)
            logging.info(f"Distance for case {pub_label}: {closest_distance}")

            # FIXED: Changed >= to <= (lower distance = better match)
            # Distance of 0.0 = perfect match, should be ACCEPTED
            # Distance of 5.0 = poor match, should be REJECTED
            if closest_distance <= distance_threshold:
                # Get the index of the predicted registered case
                predicted_idx = knn.predict([face_encoding])[0]
                # Get the original UUID of the registered case
                reg_label = original_reg_labels[predicted_idx]
                # Store the match
                matched_images[reg_label].append(pub_label)
                logging.info(
                    f"MESH FALLBACK MATCH: Public case {pub_label} -> Registered case {reg_label} (distance: {closest_distance})"
                )
        except Exception as e:
            logging.error(f"Error processing public case {pub_label}: {str(e)}\n{traceback.format_exc()}")
            continue

    logging.info(f"Matching complete. Found {len(matched_images)} matches")
    return {"status": True, "result": matched_images}


if __name__ == "__main__":
    result = match()
    print(result)