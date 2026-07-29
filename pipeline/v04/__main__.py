import preprocessing
import modeling

print("🚀 [1/2] 데이터 전처리 파이프라인 시작...")
preprocessing.run_preprocessing()

print("🚀 [2/2] 모델링 파이프라인 시작...")
modeling.run_modeling()

print("🎉 전체 파이프라인(v04) 실행완료")