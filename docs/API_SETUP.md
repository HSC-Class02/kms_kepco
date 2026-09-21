# OpenDART API 설정

## 발급
OpenDART에서 인증키를 발급합니다.

## GitHub Secret
Repository → Settings → Secrets and variables → Actions → New repository secret

- Name: `DART_API_KEY`
- Secret: 40자리 OpenDART 인증키

## 로컬
```bash
export DART_API_KEY="..."
python -m src.main
```

## 중요한 보안 원칙
- API Key를 코드에 하드코딩하지 않습니다.
- README, dashboard, commit message 등에 Key를 넣지 않습니다.
- GitHub Actions에서는 `${{ secrets.DART_API_KEY }}`로만 주입합니다.
