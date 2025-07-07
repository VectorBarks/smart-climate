# Contributing to Smart Climate Control

Thanks for your interest in contributing to Smart Climate Control! This is my personal pet project for creating a smarter Home Assistant climate integration, and I welcome all kinds of contributions from the community.

## About This Project

This is a personal learning project where I'm exploring machine learning applications for climate control. While I've put significant effort into making it robust and useful, please understand that this is fundamentally a personal project rather than a commercial product. That said, I genuinely appreciate any help in making it better!

## Ways to Contribute

There are many ways you can help improve this project:

### Bug Reports and Testing
- **Real-world testing**: Try the integration with your climate devices and sensors
- **Bug reports**: Report issues you encounter with clear reproduction steps
- **Edge case testing**: Test with unusual configurations or hardware combinations
- **Performance feedback**: Share how the system performs in your environment

### Feature Requests and Ideas
- **Enhancement suggestions**: Ideas for improving existing functionality
- **New features**: Propose new capabilities that would be useful
- **User experience improvements**: Suggestions for better configuration or monitoring
- **Integration ideas**: Ways to work better with other Home Assistant components

### Documentation
- **User guides**: Help improve setup and configuration instructions
- **Troubleshooting**: Add solutions for issues you've encountered and solved
- **Examples**: Share working configurations for different hardware setups
- **Translation**: Help translate the integration to other languages

### Code Contributions
- **Bug fixes**: Fix issues you've identified and can solve
- **Feature implementation**: Code new features or improvements
- **Testing**: Add or improve unit tests and integration tests
- **Code quality**: Refactoring, optimization, and cleanup

## Getting Started

### Development Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/VectorBarks/smart-climate.git
   cd smart-climate
   ```

2. **Set up Home Assistant development environment**:
   - Install Home Assistant in development mode
   - Copy the integration to your `custom_components` directory
   - Configure test devices and sensors

3. **Install development dependencies**:
   ```bash
   pip install -r requirements_dev.txt
   ```

4. **Run tests**:
   ```bash
   pytest tests/
   ```

## Code Guidelines

### General Principles
- **Keep it simple**: I prefer readable code over clever optimizations
- **Test your changes**: Add tests for new features and verify existing tests pass
- **Follow existing patterns**: Look at the existing code style and match it
- **Document as you go**: Add comments for complex logic and update docstrings

### Python Code Style
- Follow PEP 8 for general formatting
- Use type hints where helpful
- Keep functions focused and reasonably sized
- Use meaningful variable and function names
- Add docstrings for public methods and classes

### Testing Requirements
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Real hardware testing**: Test with actual climate devices when possible
- **TDD approach**: Write tests before implementing features (when practical)

### Home Assistant Integration Standards
- Follow Home Assistant's integration development guidelines
- Use appropriate entity types and device classes
- Handle entity state properly and provide useful attributes
- Implement proper error handling and logging
- Support configuration through both UI and YAML

## Submitting Changes

### Issues
When reporting bugs or requesting features:

1. **Search existing issues** to avoid duplicates
2. **Provide clear details**:
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Home Assistant version and integration version
   - Climate device and sensor details
   - Relevant log entries

3. **Use issue templates** when available

### Pull Requests
When submitting code changes:

1. **Fork the repository** and create a feature branch
2. **Make your changes**:
   - Follow the code guidelines above
   - Add tests for new functionality
   - Update documentation if needed
   - Ensure all tests pass

3. **Submit a pull request**:
   - Provide a clear description of changes
   - Reference related issues
   - Include testing steps
   - Keep changes focused and reasonably sized

4. **Be responsive** to feedback and questions

## Testing Your Changes

### Automated Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components.smart_climate

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Manual Testing
- Test with your actual climate devices
- Try different configuration scenarios
- Test mode switching and manual overrides
- Verify behavior with sensor failures
- Check Home Assistant UI integration

## Communication

### Be Respectful
- Keep discussions constructive and friendly
- Assume good intentions from others
- Focus on the technical aspects rather than personal preferences
- Help newcomers feel welcome

### Getting Help
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For general questions and ideas
- **Pull Request Comments**: For code review discussions

## Development Process

### Release Cycle
I don't have a formal release schedule - updates happen when features are ready and well-tested. Major changes go through more thorough testing before release.

### Code Review
I review all pull requests personally. I may ask questions or request changes to ensure code quality and consistency with the project's goals.

### Backwards Compatibility
I try to maintain backwards compatibility for configuration and APIs, but as a personal project, I may occasionally make breaking changes if they significantly improve the system.

## Recognition

Contributors are acknowledged in:
- Git commit history and pull request records
- README.md acknowledgments section
- Release notes for significant contributions

## License

By contributing to this project, you agree that your contributions will be licensed under the GNU General Public License v3.0, the same license as the project.

## Questions?

If you have questions about contributing that aren't covered here, feel free to:
- Open a GitHub Discussion
- Comment on relevant issues
- Reach out through the Home Assistant Community forums

Thanks for helping make Smart Climate Control better!