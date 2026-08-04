# [로드맵 02] 모델 및 알고리즘 아키텍처 고도화 (Model & Algorithm Architecture)

**문서 위치**: `docs/08_future_roadmap/02_model_and_algorithm_architecture.md`  
**주요 제안자**: 김기호  
**작성일시**: 2026-08-04  

---

## 1. 개요 및 배경

기존 3-Class 독립 다중 분류(Multiclass Classification) 방식은 `retained` → `weakened` → `stopped`로 이어지는 타겟 클래스 간의 **서열(Order)과 위계 구조**를 완전하게 반영하지 못하는 한계가 있습니다. 본 로드맵은 클래스 간 서열을 고려한 **순서형 분류(Ordinal Classification)** 및 **단계별 이진 분류(Two-Stage Binary)** 방법론 도입 계획을 다룹니다.

---

## 2. 세부 과제 및 기술 스펙

### 과제 2.1: 2단계 이진 분류(Two-Stage Binary) 분할 학습
- **개념**: 3-Class 문제를 타겟의 심화 단계에 따라 2개의 계층적 이진 분류 문제로 분할 학습.
  - **Model 1 (지위 상실 감지)**: `retained` vs `(weakened + stopped)`
  - **Model 2 (완전 이탈 감지)**: `(retained + weakened)` vs `stopped`
- **확률 조합 모델링**:
  - `P(약화 이상) = Model 1의 긍정 확률`
  - `P(중단 이상) = Model 2의 긍정 확률`

### 과제 2.2: 순서 제약(Ordinal Constraint)을 통한 논리 모순 방지
- **독립 모델의 문제점**: 두 이진 분류기를 개별 학습시킬 경우 `P(중단 이상) > P(약화 이상)`과 같은 논리적 모순 발생 가능성 존재.
- **해결 알고리즘**:
  1. **단조성 제약(Monotonicity Constraint) 적용**: `P(stopped) ≤ P(at-risk)` 대소 관계가 항상 유지되도록 캘리브레이션(Calibration) 후처리 적용.
  2. **전용 Ordinal Classification 손실함수**: Frank and Hall 방식 또는 CORAL(Consistent Rank Logits) 알고리즘을 도입하여 딥러닝 신경망 내부에서 위계 구조를 연산하도록 구현.

---

## 3. 기대 효과

- **예측 결과의 논리성 및 신뢰도 확보**: 클래스 간 위계 모순을 100% 방지.
- **CRM 위험 점수 단기/장기 분리**: 단기 위험(`weakened`)과 장기 완전 이탈(`stopped`)의 세분화된 확률값 산출을 통해 CRM 마케팅 메시지 차등화 가능.