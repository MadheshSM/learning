# ti-backend Project Conventions Reference

## Path Aliases (use these instead of relative imports)

| Alias           | Resolves To                      |
| --------------- | -------------------------------- |
| `@shared`       | `src/shared/index`               |
| `@entities`     | `src/shared/entities/index`      |
| `@enum`         | `src/shared/enum/index`          |
| `@str`          | `src/shared/strings/index`       |
| `@guards`       | `src/shared/guards/index`        |
| `@decorators`   | `src/shared/decorators/index`    |
| `@interceptors` | `src/shared/interceptors/index`  |
| `@filters`      | `src/shared/filters/index`       |
| `@validators`   | `src/shared/validators/index`    |
| `@response-map` | `src/shared/http-response/index` |
| `@env`          | `src/environment`                |

## Shared Utilities Available

### Error handling (`@shared`)

- `getErrorMessage(error: unknown): string` - safely extract message
- `getErrorStack(error: unknown): string` - safely extract stack

### Response (`@response-map`)

- `constructResponse(success: boolean, data: any, statusCode?: number)`

### Constants (`@str`)

- `TEXT.VALIDATION_ERROR_MESSAGE.COMMON.*` - common validation messages
- `TEXT.VALIDATION_ERROR_MESSAGE.AUTH.*` - auth error messages
- `TEXT.VALIDATION_ERROR_MESSAGE.USER.*` - user error messages
- `TEXT.VALIDATION_ERROR_MESSAGE.FORM.*` - form error messages
- `TEXT.VALIDATION_ERROR_MESSAGE.MEETING.*` - meeting error messages
- `TEXT.COMMON_LOGS.*` - common log messages
- `TEXT.GENERAL.*` - general text constants

### Database strings (`src/shared/strings/database.string.ts`)

- Database-related string constants

### Pagination (`src/shared/utils/listapi-pagination.ts`)

- List API pagination helpers

### Other utilities (`src/shared/utils/`)

- `helpers.ts` - general helper functions
- `constants.ts` - shared constants
- `error.utils.ts` - error utilities
- `circuit-breaker.ts` - circuit breaker pattern
- `retry.utils.ts` - retry utilities
- `document.ts` - document utilities
- `setting.util.ts` - settings utilities

## Shared Interfaces (`src/shared/interfaces/`)

Check before creating new interfaces:

- `selector-list.interface.ts` - selector list interface
- `activity/activity-log.interface.ts` - activity log
- `contracts/*.contract.ts` - service contracts (activity, excel, mail, vault, workflow)
- `excel.interface.ts` - excel import/export
- `notification.interface.ts` - notification
- `workflow-details.interface.ts` - workflow details
- `jwt/*.interface.ts` - JWT payload/response types
- `external-api/*.types.ts` - external API types (APS, mail, PowerBI, S3, SFTP, STOMP, Vault)

## Shared Enums (`src/shared/enum/`)

Check before creating new enums:

- `appEntity.enum.ts` - application entity types
- `user.enum.ts` - user-related enums
- `S3-LogEvent.enum.ts` - S3 log events
- `twilio/twilio-verify-status.type.ts` - Twilio status types

## NestJS Exception Classes (import from `@nestjs/common`)

- `BadRequestException` - 400 validation failures
- `UnauthorizedException` - 401 auth failures
- `ForbiddenException` - 403 permission denied
- `NotFoundException` - 404 entity not found
- `ConflictException` - 409 duplicate/conflict
- `InternalServerErrorException` - 500 server errors

## Module File Organization Convention

```
src/modules/<name>/
  <name>.module.ts           # Module definition
  <name>.controller.ts       # HTTP routes (thin, delegates to service)
  <name>.service.ts          # Business logic (or facade if decomposed)
  services/                  # Sub-services (if decomposed via /refactor-service)
    <name>-<concern>.service.ts
  dto/                       # Request/response DTOs with class-validator
    create-<name>.dto.ts
    update-<name>.dto.ts
  interfaces/                # Module-specific interfaces
    index.ts                 # Barrel export
    <name>-<type>.interface.ts
  constants/                 # Module-specific constants
    index.ts                 # Barrel export
    <name>.constants.ts
  utils/                     # Module-specific utilities (2+ callers only)
    <name>.utils.ts
```
