from __future__ import annotations

import hashlib
import itertools
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize

import yaml
from pathlib import Path

# 수렴 경고 등 불필요한 경고 숨기기
warnings.filterwarnings('ignore')

# 타겟 클래스 설정값
CLASS_CODES = [0, 1, 2]
CLASS_NAMES = ['retained', 'weakened', 'stopped']
CLASS_LABELS_KO = {0: '파워 지위 유지', 1: '파워 지위 약화', 2: '리뷰 활동 중단'}
TOP_K_RATES = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
PRIMARY_TARGET_RATE = 0.20

# 평가 지표 산출 헬퍼 함수
def evaluate(y_true: np.ndarray, predictions: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predictions, labels=CLASS_CODES, zero_division=0
    )
    y_binary = label_binarize(y_true, classes=CLASS_CODES)
    result = {
        'accuracy': accuracy_score(y_true, predictions),
        'balanced_accuracy': balanced_accuracy_score(y_true, predictions),
        'macro_precision': float(precision.mean()),
        'macro_recall': float(recall.mean()),
        'macro_f1': f1_score(y_true, predictions, average='macro'),
        'weighted_f1': f1_score(y_true, predictions, average='weighted'),
        'macro_pr_auc': float(np.mean([
            average_precision_score(y_binary[:, index], scores[:, index]) for index in CLASS_CODES
        ])),
        'macro_ovr_roc_auc': roc_auc_score(y_true, scores, multi_class='ovr', average='macro'),
    }
    for index, class_name in enumerate(CLASS_NAMES):
        result[f'{class_name}_precision'] = precision[index]
        result[f'{class_name}_recall'] = recall[index]
        result[f'{class_name}_f1'] = f1[index]
        result[f'{class_name}_support'] = int(support[index])
        result[f'{class_name}_pr_auc'] = average_precision_score(y_binary[:, index], scores[:, index])
        result[f'{class_name}_roc_auc'] = roc_auc_score(y_binary[:, index], scores[:, index])
    return result

# 커스텀 임계값 예측 헬퍼 함수
def threshold_predictions(scores, weakened_threshold, stopped_threshold):
    predictions = np.zeros(len(scores), dtype=np.int8)
    is_stopped = scores[:, 2] >= stopped_threshold
    is_weakened = (~is_stopped) & (scores[:, 1] >= weakened_threshold)
    
    predictions[is_stopped] = 2
    predictions[is_weakened] = 1
    return predictions

# 혼동 행렬 산출 함수
def confusion_records(split: str, y_true: np.ndarray, predictions: np.ndarray) -> list[dict]:
    matrix = confusion_matrix(y_true, predictions, labels=CLASS_CODES)
    return [
        {
            'split': split,
            'actual_state': CLASS_NAMES[actual],
            'predicted_state': CLASS_NAMES[predicted],
            'users': int(matrix[actual, predicted]),
        }
        for actual in CLASS_CODES for predicted in CLASS_CODES
    ]

# Top-K 산출 함수
def top_k_records(split: str, y_true: np.ndarray, scores: np.ndarray) -> list[dict]:
    rankings = {
        'unified': scores[:, 1] + scores[:, 2],
        'stopped_only': scores[:, 2],
        'weakened_only': scores[:, 1],
    }
    status_loss = y_true != 0
    stopped = y_true == 2
    weakened = y_true == 1
    records = []
    for ranking_name, ranking_score in rankings.items():
        order = np.argsort(-ranking_score, kind='stable')
        for rate in TOP_K_RATES:
            users = int(np.ceil(len(y_true) * rate))
            selected = order[:users]
            captured_status = int(status_loss[selected].sum())
            captured_stopped = int(stopped[selected].sum())
            captured_weakened = int(weakened[selected].sum())
            precision = captured_status / users
            records.append({
                'split': split,
                'ranking': ranking_name,
                'target_rate': rate,
                'target_users': users,
                'status_loss_captured': captured_status,
                'status_loss_precision': precision,
                'status_loss_recall': captured_status / status_loss.sum(),
                'status_loss_lift': precision / status_loss.mean(),
                'stopped_captured': captured_stopped,
                'stopped_recall': captured_stopped / stopped.sum(),
                'weakened_captured': captured_weakened,
                'weakened_recall': captured_weakened / weakened.sum(),
            })
    return records


def load_config_and_setup():
    '''
    환경 설정 및 설정값 로드
    '''
    print("=== [Step 1] 환경 설정 및 설정값 로드 시작 ===")
    
    # 1. 프로젝트 루트 경로 탐색
    current_path = Path.cwd().resolve()
    PROJECT_ROOT = next(
        (path for path in [current_path, *current_path.parents] if (path / "configs").exists()),
        None
    )

    if PROJECT_ROOT is None:
        raise FileNotFoundError("프로젝트 루트 경로를 찾을 수 없습니다. 'configs' 폴더가 있는지 확인해주세요.")

    # 2. Config 파일 로드
    CONFIG_PATH = PROJECT_ROOT / "configs" / "analysis_config_v04.yaml"
    
    with CONFIG_PATH.open(mode="r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # 3. 주요 환경 설정값 추출
    # 프로젝트 기본 설정
    COHORT_VERSION = config["project"]["cohort_version"]
    RANDOM_STATE = config["project"]["random_state"]
    
    # 코호트 및 분할 연도 설정
    MIN_SELECTION_YEAR = config['cohort']['minimum_selection_year']
    VALIDATION_YEAR = config['cohort']['validation_selection_year']
    TEST_YEAR = config['cohort']['test_selection_year']

    # 다중 클래스(리텐션 상태) 레이블 매핑
    RETAINED_CLASS = config['retention_state']['retained_class'] # 0 (유지)
    WEAKENED_CLASS = config['retention_state']['weakened_class'] # 1 (약화)
    STOPPED_CLASS = config['retention_state']['stopped_class']   # 2 (중단)

    # 4. 입출력 폴더(디렉토리) 경로 설정 및 생성
    DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
    MODELS_DIR = PROJECT_ROOT / "models"
    
    REPORTS_TABLE_DIR = PROJECT_ROOT / "reports" / "tables"
    REPORTS_MODEL_DIR = PROJECT_ROOT / "reports" / "modeling"
    PREDICTIONS_DIR = DATA_PROCESSED_DIR / "predictions"

    # 디렉토리가 없으면 자동으로 생성
    for directory in [MODELS_DIR, REPORTS_TABLE_DIR, REPORTS_MODEL_DIR, PREDICTIONS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        
    # 5. 전체 입력/최종 산출물 파일 경로 명시적 정의
    # [입력 데이터]
    INPUT_DATA_PATH = DATA_PROCESSED_DIR / f"modeling_dataset_rolling_{COHORT_VERSION}.parquet"
    V02_METADATA_PATH = MODELS_DIR / 'final_core_hgb_metadata_v02.json'
    V03_METADATA_PATH = MODELS_DIR / 'final_core_logistic_multiclass_metadata_v03.json'
    
    # [모델 및 메타데이터 산출물]
    MODEL_OUTPUT_PATH = MODELS_DIR / f"final_core_logistic_multiclass_{COHORT_VERSION}.joblib"
    METADATA_OUTPUT_PATH = MODELS_DIR / f"final_core_logistic_multiclass_metadata_{COHORT_VERSION}.json"
    
    # [최종 예측 프로필]
    PROFILE_OUTPUT_PATH = PREDICTIONS_DIR / f"final_test_retention_profiles_{COHORT_VERSION}.parquet"
    
    # [보고서 및 검증 결과 표 산출물 (5종)]
    PERFORMANCE_REPORT_PATH = REPORTS_MODEL_DIR / f"multiclass_model_performance_{COHORT_VERSION}.md"
    VALIDATION_RESULTS_PATH = REPORTS_TABLE_DIR / f"multiclass_validation_results_{COHORT_VERSION}.csv"
    MODEL_CANDIDATES_PATH = REPORTS_TABLE_DIR / f"multiclass_model_candidates_{COHORT_VERSION}.csv"
    CONFUSION_MATRIX_PATH = REPORTS_TABLE_DIR / f"multiclass_confusion_matrix_{COHORT_VERSION}.csv"
    TOP_K_PERFORMANCE_PATH = REPORTS_TABLE_DIR / f"multiclass_top_k_performance_{COHORT_VERSION}.csv"
    
    # 설정값들을 하나의 딕셔너리로 묶어서 반환 (이후 단계에서 사용)
    setup_vars = {
        # 기본 설정값
        "RANDOM_STATE": RANDOM_STATE,
        "COHORT_VERSION": COHORT_VERSION,
        "MIN_SELECTION_YEAR": MIN_SELECTION_YEAR,
        "VALIDATION_YEAR": VALIDATION_YEAR,
        "TEST_YEAR": TEST_YEAR,
        "RETAINED_CLASS": RETAINED_CLASS,
        "WEAKENED_CLASS": WEAKENED_CLASS,
        "STOPPED_CLASS": STOPPED_CLASS,
        
        # 파일 경로 객체
        "INPUT_DATA_PATH": INPUT_DATA_PATH,
        'V02_METADATA_PATH': V02_METADATA_PATH,
        'V03_METADATA_PATH': V03_METADATA_PATH,
        "MODEL_OUTPUT_PATH": MODEL_OUTPUT_PATH,
        "METADATA_OUTPUT_PATH": METADATA_OUTPUT_PATH,
        "PROFILE_OUTPUT_PATH": PROFILE_OUTPUT_PATH,
        "PERFORMANCE_REPORT_PATH": PERFORMANCE_REPORT_PATH,
        "VALIDATION_RESULTS_PATH": VALIDATION_RESULTS_PATH,
        "MODEL_CANDIDATES_PATH": MODEL_CANDIDATES_PATH,
        "CONFUSION_MATRIX_PATH": CONFUSION_MATRIX_PATH,
        "TOP_K_PERFORMANCE_PATH": TOP_K_PERFORMANCE_PATH,
    }

    print(f" - Random State: {RANDOM_STATE}")
    print(f" - Train/Val 기간: {MIN_SELECTION_YEAR} ~ {VALIDATION_YEAR}")
    print(f" - Test 연도: {TEST_YEAR}")
    print("✅ 환경 설정 및 디렉토리 준비 완료\n")
    
    return setup_vars


def load_and_prepare_data(setup_vars):
    '''
    데이터 로드 및 피처 정제
    '''
    print("=== [Step 2] 데이터 로드 및 피처 정제 시작 ===")
    
    # 1. 이전 Step에서 정의한 경로에서 Parquet 데이터 로드
    input_path = setup_vars["INPUT_DATA_PATH"]
    print(f"데이터 로드 중: {input_path}")
    
    try:
        df = pd.read_parquet(input_path)
    except FileNotFoundError:
        print(f"❌ 에러: {input_path} 파일을 찾을 수 없습니다. 전처리 파이프라인을 먼저 실행했는지 확인해주세요.")
        return None

    # 2. 메타데이터/타깃 컬럼과 모델 학습용 피처(X) 분리
    # 자동으로 43개의 Core 피처 추출
    feature_columns = json.loads(setup_vars['V02_METADATA_PATH'].read_text(encoding='utf-8'))['feature_columns']
    
    print(f"추출된 핵심 피처(Core Features) 개수: {len(feature_columns)}개")

    # 3. Train/Validation(학습/검증) 데이터와 Final Test(최종 테스트) 데이터 분할
    # split_v04 컬럼의 라벨을 활용하여 안전하게 분할 (2010~2017: pool, 2018: test)
    train_val_mask = df['split_v04'].isin(['train', 'validation'])
    test_mask = df['split_v04'] == 'test'
    
    # [3-1] 풀(Pool) 데이터 구성: 하이퍼파라미터 튜닝 및 교차 검증용
    df_pool = df[train_val_mask].copy()
    X_pool = df_pool[feature_columns]
    y_pool = df_pool['retention_state']
    meta_pool = df_pool[['sample_id', 'user_id', 'selection_year']]
    
    # [3-2] 최종 테스트 데이터 구성: 최종 성능 평가 및 CRM 타겟팅 프로필용
    df_test = df[test_mask].copy()
    X_test = df_test[feature_columns]
    y_test = df_test['retention_state']
    meta_test = df_test[['sample_id', 'user_id', 'selection_year']]
    
    print(f" - Train/Validation 데이터 크기 ({setup_vars['MIN_SELECTION_YEAR']}~{setup_vars['VALIDATION_YEAR']}): {X_pool.shape[0]:,}건")
    print(f" - Final Test 데이터 크기 ({setup_vars['TEST_YEAR']}): {X_test.shape[0]:,}건")
    print("✅ 데이터 로드 및 피처 정제 완료\n")
    
    # 4. 다음 스텝(교차검증 및 학습)으로 넘겨줄 데이터 패키징
    data_vars = {
        "feature_columns": feature_columns,
        
        # 모델 학습용 데이터
        "X_pool": X_pool,
        "y_pool": y_pool,
        "meta_pool": meta_pool,
        
        # 최종 평가용 데이터
        "X_test": X_test,
        "y_test": y_test,
        "meta_test": meta_test,
        
        # CRM 우선순위 프로필 생성 시 결합을 위해 원본 test 데이터프레임도 보존
        "df_test_raw": df_test 
    }
    
    return data_vars


def create_expanding_window_cv(setup_vars, data_vars):
    '''
    시간 구조 보존형 5-Fold 교차 검증
    '''
    print("=== [Step 3] 시간 구조 보존형 교차 검증(Expanding Window CV) 구축 ===")
    
    # 2단계에서 넘어온 meta_pool 데이터 사용
    meta_pool = data_vars["meta_pool"]
    
    # 순차적 인덱스 접근을 위해 numpy 배열로 변환
    years = meta_pool['selection_year'].to_numpy()
    
    cv_splits = []
    
    # 검증 연도(Validation Year) 설정: 2013년부터 2017년까지 5-Fold
    # (2010~2012년은 최소한의 초기 학습 데이터로 사용)
    validation_years = [i for i in range(setup_vars['VALIDATION_YEAR'] - 4, setup_vars['VALIDATION_YEAR'] + 1)]
    
    for fold, val_year in enumerate(validation_years, start=1):
        # [학습 데이터 조건] 최소 선정 연도부터 검증 연도 직전(val_year - 1)까지
        train_mask = (years >= setup_vars['MIN_SELECTION_YEAR']) & (years < val_year)
        
        # [검증 데이터 조건] 해당 검증 연도(val_year) 단일 연도
        val_mask = (years == val_year)
        
        # 조건에 맞는 행의 절대 인덱스(0부터 시작하는 정수형 인덱스) 추출
        train_idx = np.where(train_mask)[0]
        val_idx = np.where(val_mask)[0]
        
        # Scikit-Learn의 커스텀 CV 형식인 (train_indices, val_indices) 튜플로 저장
        cv_splits.append((train_idx, val_idx))
        
        print(f" - Fold {fold}: [학습] {setup_vars['MIN_SELECTION_YEAR']}~{val_year-1} ({len(train_idx):>5,}건) ➔ [검증] {val_year} ({len(val_idx):>4,}건)")

    print("✅ 5-Fold Expanding Window CV 스플릿 준비 완료\n")
    
    # 다음 스텝을 위해 data_vars에 cv_splits 리스트 추가
    data_vars["cv_splits"] = cv_splits
    
    return data_vars


def explore_hyperparameters_and_thresholds(setup_vars, data_vars):
    '''
    모델 파이프라인 및 하이퍼파라미터/임계값 탐색
    '''
    print("=== [Step 4] 모델 파이프라인 및 하이퍼파라미터/임계값 탐색 시작 ===")
    
    X_pool = data_vars["X_pool"]
    y_pool = data_vars["y_pool"]
    meta_pool = data_vars["meta_pool"]
    cv_splits = data_vars["cv_splits"]
    
    # 1. 탐색 공간 (Grid) 정의 (원본 노트북 기준)
    PENALTIES = ['l1', 'l2']
    C_VALUES = [0.01, 0.03, 0.10, 0.30, 1.00]
    CLASS_WEIGHT_OPTIONS = {'none': None, 'balanced': 'balanced'}
    WEAKENED_THRESHOLDS = [0.30, 0.36, 0.42]
    STOPPED_THRESHOLDS = [0.35, 0.45, 0.55]
    
    candidate_rows = []
    model_specs = list(itertools.product(PENALTIES, C_VALUES, CLASS_WEIGHT_OPTIONS.items()))
    
    print(f"총 {len(model_specs)}개의 모델 스펙 × {len(WEAKENED_THRESHOLDS) * len(STOPPED_THRESHOLDS)}개의 임계값 조합 평가 중...")
    
    # 2. 하이퍼파라미터 모델 훈련 루프
    for penalty, c_value, (class_weight_name, class_weight) in model_specs:
        oof_parts = []
        fold_pr_auc = []
        fold_roc_auc = []
        convergence_iterations = []
        candidate_id = f'{penalty}_C{c_value:g}_{class_weight_name}'
        
        # 3. 시간 구조 보존형 교차 검증 (Expanding Window)
        for fold_idx, (train_idx, val_idx) in enumerate(cv_splits):
            X_train, y_train = X_pool.iloc[train_idx], y_pool.iloc[train_idx]
            X_val, y_val = X_pool.iloc[val_idx], y_pool.iloc[val_idx]
            
            # 모델(파이프라인) 빌드
            model = Pipeline([
                ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
                ('scaler', StandardScaler()),
                ('model', LogisticRegression(
                    solver='saga',
                    penalty=penalty,
                    C=c_value,
                    class_weight=class_weight,
                    max_iter=5_000,
                    tol=1e-3,
                    random_state=setup_vars["RANDOM_STATE"]
                ))
            ])
            
            # 학습 및 검증 폴드 예측
            model.fit(X_train, y_train)
            scores = model.predict_proba(X_val)
            argmax_predictions = scores.argmax(axis=1).astype('int8')
            
            # 검증 폴드별 Base 지표 평가
            base_metrics = evaluate(y_val.to_numpy(), argmax_predictions, scores)
            fold_pr_auc.append(base_metrics['macro_pr_auc'])
            fold_roc_auc.append(base_metrics['macro_ovr_roc_auc'])
            convergence_iterations.append(int(model.named_steps['model'].n_iter_.max()))
            
            # 해당 Fold의 OOF 예측 결과 저장
            part = meta_pool.iloc[val_idx][['sample_id', 'selection_year']].copy()
            part['retention_state'] = y_val.to_numpy()
            part[['retained_score', 'weakened_score', 'stopped_score']] = scores
            oof_parts.append(part)

        # 4. 전체 OOF 데이터 병합 및 임계값(Threshold) 루프
        oof = pd.concat(oof_parts, ignore_index=True)
        oof_scores = oof[['retained_score', 'weakened_score', 'stopped_score']].to_numpy()
        oof_y = oof['retention_state'].to_numpy()
        
        for weakened_threshold, stopped_threshold in itertools.product(WEAKENED_THRESHOLDS, STOPPED_THRESHOLDS):
            predictions = threshold_predictions(oof_scores, weakened_threshold, stopped_threshold)
            metrics = evaluate(oof_y, predictions, oof_scores)
            
            # 최종 산출물(Row) 생성 (노트북 컬럼 구성 완벽 일치)
            candidate_rows.append({
                'candidate_id': candidate_id,
                'penalty': penalty,
                'C': c_value,
                'class_weight': class_weight_name,
                'weakened_threshold': weakened_threshold,
                'stopped_threshold': stopped_threshold,
                'validation_samples': len(oof),
                'fold_macro_pr_auc_mean': float(np.mean(fold_pr_auc)),
                'fold_macro_pr_auc_std': float(np.std(fold_pr_auc, ddof=1)),
                'fold_macro_roc_auc_mean': float(np.mean(fold_roc_auc)),
                'maximum_iterations': max(convergence_iterations),
                **{f'oof_{key}': value for key, value in metrics.items()},
            })

    # 5. 모델 후보군 데이터프레임 생성 및 정렬 (stable sort)
    candidate_df = pd.DataFrame(candidate_rows)
    candidate_df = candidate_df.sort_values(
        ['oof_macro_f1', 'oof_macro_pr_auc', 'oof_balanced_accuracy', 'oof_stopped_recall', 'oof_weakened_recall'],
        ascending=False,
        kind='stable',
    ).reset_index(drop=True)
    
    # 순위 부여 및 선택 여부(1등) 플래그 생성
    candidate_df.insert(0, 'selection_rank', np.arange(1, len(candidate_df) + 1))
    candidate_df['selected'] = candidate_df['selection_rank'].eq(1)
    
    # CSV 저장
    output_path = setup_vars["MODEL_CANDIDATES_PATH"]
    candidate_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"✅ 그리드 탐색 완료 산출물 저장: {output_path}")
    
    # 6. 최적의 조건(1등 조합) 추출 및 다음 스텝으로 전달
    best_candidate = candidate_df.iloc[0]
    best_params = {
        'penalty': best_candidate['penalty'],
        'C': best_candidate['C'],
        'class_weight_name': str(best_candidate['class_weight']),
        'class_weight': None if best_candidate['class_weight'] == 'none' else best_candidate['class_weight']
    }
    best_thresholds = {
        'weakened_threshold': best_candidate['weakened_threshold'],
        'stopped_threshold': best_candidate['stopped_threshold']
    }
    
    print("\n👑 [최적의 모델 조건 선정 (Rank 1)]")
    print(f" - Candidate ID: {best_candidate['candidate_id']}")
    print(f" - Best Thresholds: W(>= {best_thresholds['weakened_threshold']}), S(>= {best_thresholds['stopped_threshold']})")
    print(f" - Best OOF Macro F1: {best_candidate['oof_macro_f1']:.4f}\n")
    
    data_vars["best_params"] = best_params
    data_vars["best_thresholds"] = best_thresholds
    
    return data_vars


def train_evaluate_and_profile(setup_vars, data_vars):
    '''
    최종 모델 평가 및 CRM 프로필/메타데이터 생성
    '''
    print("=== [Step 5 & 6] OOF 재평가, 최종 학습, CRM 프로필 및 메타데이터 생성 ===")
    warnings.filterwarnings('ignore', category=ConvergenceWarning)
    
    # 1. 데이터 및 파라미터 로드
    X_pool = data_vars["X_pool"]
    y_pool = data_vars["y_pool"]
    meta_pool = data_vars["meta_pool"]
    cv_splits = data_vars["cv_splits"]
    feature_columns = data_vars["feature_columns"]
    
    X_test = data_vars["X_test"]
    y_test = data_vars["y_test"]
    meta_test = data_vars["meta_test"]
    
    best_params = data_vars["best_params"]
    w_thresh = data_vars["best_thresholds"]["weakened_threshold"]
    s_thresh = data_vars["best_thresholds"]["stopped_threshold"]
    
    validation_records = []
    confusion_rows = []
    selected_oof_parts = []
    
    # =====================================================================
    # [OOF 검증 재수행 및 Fold별 세부 기록 생성]
    # =====================================================================
    validation_years = [i for i in range(setup_vars['VALIDATION_YEAR'] - 4, setup_vars['VALIDATION_YEAR'] + 1)] # cv_splits와 매핑
    
    for fold_number, ((train_idx, val_idx), val_year) in enumerate(zip(cv_splits, validation_years), start=1):
        X_tr, y_tr = X_pool.iloc[train_idx], y_pool.iloc[train_idx]
        X_va, y_va = X_pool.iloc[val_idx], y_pool.iloc[val_idx]
        
        model = Pipeline([
            ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
            ('scaler', StandardScaler()),
            ('model', LogisticRegression(
                solver='saga',
                penalty=best_params['penalty'], 
                C=best_params['C'],
                class_weight=best_params['class_weight'],
                max_iter=5_000, 
                tol=0.001, 
                random_state=setup_vars["RANDOM_STATE"]
            ))
        ])
        
        model.fit(X_tr, y_tr)
        scores = model.predict_proba(X_va)
        predictions = threshold_predictions(scores, w_thresh, s_thresh)
        
        # Validation Records 기록
        validation_records.append({
            'record_type': 'fold',
            'split': f'fold_{fold_number}',
            'train_selection_years': f'2010~{val_year-1}',
            'validation_selection_year': val_year,
            'train_samples': len(X_tr),
            'validation_samples': len(X_va),
            **evaluate(y_va.to_numpy(), predictions, scores),
        })
        
        # Confusion Matrix 기록
        confusion_rows.extend(confusion_records(f'validation_{val_year}', y_va.to_numpy(), predictions))
        
        # OOF Parts 저장
        part = meta_pool.iloc[val_idx].copy()
        part['retention_state'] = y_va.to_numpy()
        part[['retained_score', 'weakened_score', 'stopped_score']] = scores
        selected_oof_parts.append(part)

    # Fold Summary (평균, 표준편차) 계산
    fold_df = pd.DataFrame(validation_records)
    metric_columns = [col for col in fold_df.columns if col not in {
        'record_type', 'split', 'train_selection_years', 'validation_selection_year', 'train_samples', 'validation_samples'
    }]
    
    summary_rows = []
    for statistic in ['mean', 'std']:
        row = {
            'record_type': statistic, 'split': 'time_5_fold',
            'train_selection_years': 'expanding_2010~2016',
            'validation_selection_year': pd.NA, 'train_samples': pd.NA, 'validation_samples': pd.NA,
        }
        for column in metric_columns:
            row[column] = fold_df[column].mean() if statistic == 'mean' else fold_df[column].std(ddof=1)
        summary_rows.append(row)

    # Pooled OOF 결산
    oof_df = pd.concat(selected_oof_parts, ignore_index=True)
    oof_scores = oof_df[['retained_score', 'weakened_score', 'stopped_score']].to_numpy()
    oof_y = oof_df['retention_state'].to_numpy()
    oof_predictions = threshold_predictions(oof_scores, w_thresh, s_thresh)
    
    oof_record = {
        'record_type': 'pooled_oof', 'split': 'time_5_fold',
        'train_selection_years': 'expanding_2010~2016',
        'validation_selection_year': pd.NA, 'train_samples': pd.NA, 'validation_samples': len(oof_df),
        **evaluate(oof_y, oof_predictions, oof_scores),
    }

    # =====================================================================
    # [최종 모델 학습 및 Test Data 검증]
    # =====================================================================
    print("최종 모델 전체 데이터 재학습 및 테스트 검증 중...")
    final_model = Pipeline([
        ('imputer', SimpleImputer(strategy='median', add_indicator=True)),
        ('scaler', StandardScaler()),
        ('model', LogisticRegression(
            solver='saga',
            penalty=best_params['penalty'], 
            C=best_params['C'], 
            class_weight=best_params['class_weight'],
            max_iter=5_000, 
            tol=0.001, 
            random_state=setup_vars["RANDOM_STATE"]
        ))
    ])
    
    final_model.fit(X_pool, y_pool)
    test_scores = final_model.predict_proba(X_test)
    test_predictions = threshold_predictions(test_scores, w_thresh, s_thresh)
    test_y = y_test.to_numpy()
    test_metrics = evaluate(test_y, test_predictions, test_scores)
    
    test_record = {
        'record_type': 'final_test', 'split': 'selection_2018_target_2019',
        'train_selection_years': '2010~2017', 'validation_selection_year': 2018,
        'train_samples': len(X_pool), 'validation_samples': len(X_test),
        **test_metrics,
    }

    # =====================================================================
    # [결과 CSV 저장 (Validation, Confusion, Top-K)]
    # =====================================================================
    validation_df = pd.concat([fold_df, pd.DataFrame(summary_rows), pd.DataFrame([oof_record, test_record])], ignore_index=True)
    validation_df.to_csv(setup_vars["VALIDATION_RESULTS_PATH"], index=False, encoding='utf-8-sig')

    confusion_rows.extend(confusion_records('pooled_oof', oof_y, oof_predictions))
    confusion_rows.extend(confusion_records('final_test', test_y, test_predictions))
    confusion_df = pd.DataFrame(confusion_rows)
    confusion_df.to_csv(setup_vars["CONFUSION_MATRIX_PATH"], index=False, encoding='utf-8-sig')

    top_k_df = pd.DataFrame(top_k_records('pooled_oof', oof_y, oof_scores) + top_k_records('final_test', test_y, test_scores))
    top_k_df.to_csv(setup_vars["TOP_K_PERFORMANCE_PATH"], index=False, encoding='utf-8-sig')

    # =====================================================================
    # [CRM 프로필 생성 및 Parquet 저장]
    # =====================================================================
    print("CRM 타겟팅 우선순위 프로필 생성 중...")
    profile_df = data_vars["df_test_raw"].copy()
    profile_df['retention_state_label'] = profile_df['retention_state'].map(CLASS_LABELS_KO)
    profile_df[['retained_score', 'weakened_score', 'stopped_score']] = test_scores
    profile_df['priority_score'] = profile_df['weakened_score'] + profile_df['stopped_score']
    profile_df['predicted_state'] = test_predictions
    profile_df['predicted_state_label'] = profile_df['predicted_state'].map(CLASS_LABELS_KO)
    
    # 랭킹 및 상위 20% 마킹
    profile_df['priority_rank'] = profile_df['priority_score'].rank(method='first', ascending=False).astype(int)
    profile_df['priority_top_percent'] = profile_df['priority_rank'] / len(profile_df) * 100
    target_users = int(np.ceil(len(profile_df) * PRIMARY_TARGET_RATE))
    profile_df['selected_for_crm'] = profile_df['priority_rank'].le(target_users).astype('int8')
    
    profile_df = profile_df.sort_values(['priority_rank', 'sample_id']).reset_index(drop=True)
    profile_df.to_parquet(setup_vars["PROFILE_OUTPUT_PATH"], index=False)

    # =====================================================================
    # [모델 Joblib 직렬화 및 메타데이터 JSON 생성]
    # =====================================================================
    print("최종 모델 저장 및 메타데이터 파일 생성 중...")
    joblib.dump(final_model, setup_vars["MODEL_OUTPUT_PATH"])
    model_checksum = hashlib.sha256(Path(setup_vars["MODEL_OUTPUT_PATH"]).read_bytes()).hexdigest()
    
    # 그룹별 성능 평가 (이전 활동 기록 여부)
    subgroup_metrics = {}
    for group_value, group_name in [(0, 'no_prior_activity'), (1, 'has_prior_activity')]:
        mask = profile_df['prior_activity_available'].eq(group_value).to_numpy()
        subgroup_metrics[group_name] = evaluate(test_y[mask], test_predictions[mask], test_scores[mask])

    top20 = top_k_df[(top_k_df['split'].eq('final_test')) & (top_k_df['ranking'].eq('unified')) & (top_k_df['target_rate'].eq(PRIMARY_TARGET_RATE))].iloc[0]
    
    v03_metadata = json.loads(setup_vars['V03_METADATA_PATH'].read_text(encoding='utf-8'))
    metadata = {
        'version': setup_vars["COHORT_VERSION"],
        'model_name': f'Core Multiclass Logistic {setup_vars["COHORT_VERSION"]}',
        'model_type': 'LogisticRegression',
        'problem_type': 'multiclass_classification',
        'class_map': {'0': 'retained', '1': 'weakened', '2': 'stopped'},
        'class_labels_ko': {str(k): v for k, v in CLASS_LABELS_KO.items()},
        'label_definition': {
            'retained': 'target_review_count >= 10 and target_active_months >= 3',
            'weakened': 'target_review_count >= 1 and (target_review_count < 10 or target_active_months < 3)',
            'stopped': 'target_review_count == 0',
        },
        'cohort_definition': 'selection year review_count >= 10 and active_months >= 3; no H2 continuity filter',
        'time_structure': 'comparison Y-1, selection/feature cutoff Y, target Y+1',
        'selection_rule': 'highest pooled 5-fold macro F1; ties by PR-AUC, balanced accuracy and class recall',
        'model_parameters': {
            'penalty': best_params['penalty'],
            'C': best_params['C'],
            'solver': 'saga',
            'class_weight': best_params['class_weight_name'],
            'max_iter': 5000,
            'tol': 0.001,
            'random_state': setup_vars["RANDOM_STATE"],
        },
        'decision_thresholds': {
            'weakened_score': w_thresh,
            'stopped_score': s_thresh,
            'evaluation_order': ['stopped', 'weakened', 'retained'],
        },
        'priority_policy': {
            'score': 'weakened_score + stopped_score',
            'primary_target_rate': PRIMARY_TARGET_RATE,
        },
        'feature_set': 'activity+interval+business',
        'feature_count': len(feature_columns),
        'feature_columns': feature_columns,
        'imputed_feature_count': len(final_model.named_steps['imputer'].get_feature_names_out(feature_columns)),
        'time_folds': [
            {'train_selection_years': f'2010~{val_year-1}', 'validation_selection_year': val_year}
            for val_year in validation_years
        ],
        'final_train_selection_years': '2010~2017',
        'test_selection_year': 2018,
        'test_target_year': 2019,
        'test_samples': len(X_test),
        'test_metrics': {key: float(value) for key, value in test_metrics.items()},
        'test_subgroup_metrics': {
            group: {key: float(value) for key, value in metrics.items()}
            for group, metrics in subgroup_metrics.items()
        },
        'top20_policy': {key: float(top20[key]) for key in [
            'target_users', 'status_loss_captured', 'status_loss_precision', 'status_loss_recall',
            'status_loss_lift', 'stopped_captured', 'stopped_recall', 'weakened_captured', 'weakened_recall',
        ]},
        'v03_reference_metrics': v03_metadata['test_metrics'],
        'model_sha256': model_checksum,
        'python_version': sys.version.split()[0],
        'sklearn_version': sklearn.__version__,
        'pandas_version': pd.__version__,
        'score_warning': '클래스별 점수는 확률 보정 전 모델 점수이며 실제 상태 확률로 표현하지 않는다.',
    }
    
    Path(setup_vars["METADATA_OUTPUT_PATH"]).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )

    print(f"✅ CRM 타겟팅 산출물 및 메타데이터 JSON 저장 완료")
    print(f" - Pooled OOF Macro F1: {oof_record['macro_f1']:.4f}")
    print(f" - Final Test Macro F1: {test_metrics['macro_f1']:.4f}")

    v03_metrics = v03_metadata['test_metrics']

    report = f'''# 파워 리뷰어 3클래스 리텐션 모델 v04

## 모델 선정 원칙

- 2013~2017 확장형 시간 5-Fold에서만 규제·가중치·임계값 선택
- 선정 기준: pooled OOF Macro F1 우선, 이후 PR-AUC·Balanced Accuracy·클래스 Recall
- 최종 Train: 선정연도 2010~2017, 31,420표본
- 최종 Test: 선정연도 2018 → 타깃연도 2019, 6,533표본
- Test 결과는 모델 조건 선택에 사용하지 않음

## 선택된 조건

- Penalty: {best_params['penalty']}
- C: {best_params['C']:g}
- Class weight: {best_params['class_weight_name']}
- 약화 임계값: {w_thresh:.2f}
- 중단 임계값: {s_thresh:.2f}

## 최종 Test 성능

| 지표 | v03 참고 | v04 |
|---|---:|---:|
| Macro F1 | {v03_metrics['macro_f1']:.4f} | {test_metrics['macro_f1']:.4f} |
| Macro PR-AUC | {v03_metrics['macro_pr_auc']:.4f} | {test_metrics['macro_pr_auc']:.4f} |
| Macro ROC-AUC | {v03_metrics['macro_ovr_roc_auc']:.4f} | {test_metrics['macro_ovr_roc_auc']:.4f} |
| Balanced Accuracy | {v03_metrics['balanced_accuracy']:.2%} | {test_metrics['balanced_accuracy']:.2%} |

| 클래스 | Precision | Recall | F1 | PR-AUC |
|---|---:|---:|---:|---:|
| 유지 | {test_metrics['retained_precision']:.2%} | {test_metrics['retained_recall']:.2%} | {test_metrics['retained_f1']:.4f} | {test_metrics['retained_pr_auc']:.4f} |
| 약화 | {test_metrics['weakened_precision']:.2%} | {test_metrics['weakened_recall']:.2%} | {test_metrics['weakened_f1']:.4f} | {test_metrics['weakened_pr_auc']:.4f} |
| 중단 | {test_metrics['stopped_precision']:.2%} | {test_metrics['stopped_recall']:.2%} | {test_metrics['stopped_f1']:.4f} | {test_metrics['stopped_pr_auc']:.4f} |

v03과 v04는 코호트와 시간 구조가 다르므로 성능 수치는 단순 우열이 아니라 참고 비교로만 사용한다.

## 통합 상위 20% 정책

- 관리 대상: {int(top20['target_users']):,}명
- 실제 지위 상실 포착: {int(top20['status_loss_captured']):,}명
- 지위 상실 Precision: {top20['status_loss_precision']:.2%}
- 지위 상실 Recall: {top20['status_loss_recall']:.2%}
- 무작위 대비 Lift: {top20['status_loss_lift']:.2f}배
- 중단 포착: {int(top20['stopped_captured']):,}명, Recall {top20['stopped_recall']:.2%}
- 약화 포착: {int(top20['weakened_captured']):,}명, Recall {top20['weakened_recall']:.2%}

전체 지위 상실자가 3,949명이므로 상위 20% 정책의 Recall 이론적 최대치는 약 33.10%다.

## 제한사항

- 클래스 점수는 보정된 실제 확률이 아니다.
- 2017년 활동이 없는 후보는 결측 표시를 통해 학습하며, 초기 연도 데이터 희소성 영향이 남을 수 있다.
- CRM 개입 효과와 복귀 결과는 현재 데이터에 없다.
- v04 모델의 운영 기본값 전환은 별도 승인 후 수행한다.
'''
    setup_vars['PERFORMANCE_REPORT_PATH'].write_text(report, encoding='utf-8')

    data_vars["metadata"] = metadata
    data_vars["final_model"] = final_model

    return data_vars

# 전체 파이프라인 실행 함수
def run_modeling():
    setup_vars = load_config_and_setup()
    data_vars = load_and_prepare_data(setup_vars)
    data_vars = create_expanding_window_cv(setup_vars, data_vars)
    data_vars = explore_hyperparameters_and_thresholds(setup_vars, data_vars)
    train_evaluate_and_profile(setup_vars, data_vars)

# 모델 통합 학습 및 평가 파이프라인 실행
if __name__ == "__main__":
    run_modeling()