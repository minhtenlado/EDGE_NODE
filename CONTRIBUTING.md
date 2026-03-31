# Contribution Guidelines

Cảm ơn bạn quan tâm đến dự án này! Dưới đây là hướng dẫn để contribute:

## Quy Trình Contribution

1. **Fork** repository
2. **Clone** fork của bạn
3. **Tạo branch** mới cho feature/bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Commit** changes của bạn
   ```bash
   git commit -m "feat: description of your change"
   ```
5. **Push** đến fork
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Tạo Pull Request** với mô tả chi tiết

## Commit Message Convention

Sử dụng Conventional Commits:

```
feat: add new OCR feature
fix: resolve camera connection issue
docs: update setup documentation
style: fix code formatting
refactor: reorganize model loading
test: add unit tests for OCR
chore: update dependencies
```

## Code Style

- Python: PEP 8
- Line length: max 100 characters
- Use type hints khi có thể
- Docstrings cho tất cả functions/classes

### Format Code
```bash
black src/ --line-length 100
```

## Testing

Viết test cho mọi feature baru:

```bash
pytest tests/ --cov=src
```

## Documentation

- Update README.md nếu thay đổi API
- Add docstrings cho mới functions
- Update API.md cho MQTT topics mới

## Issues

- Tìm **existing issues** trước khi tạo issue mới
- Provide **clear description** và **steps to reproduce**
- Include **system info** (Raspberry Pi model, Python version, etc.)

## Code Review

Tất cả PRs cần review trước merge. Hãy:
- Respond to feedback
- Update code nếu cần
- Re-request review sau update

## License

Mọi contribution coi như bạn agree mit MIT License.

Cảm ơn! 🎉
