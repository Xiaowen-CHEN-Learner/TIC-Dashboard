# Optional. Serves the built dashboard as a static site, for example on Cloud Run.
# There is no sign-in: keep the service private unless you mean to publish it.
FROM python:3.12-slim AS build
WORKDIR /app
COPY . .
RUN python tools/check.py && python tools/build_static.py --single

FROM python:3.12-slim
WORKDIR /srv
COPY --from=build /app/site ./site
ENV PORT=8080
EXPOSE 8080
USER nobody
CMD ["sh", "-c", "exec python -m http.server \"$PORT\" --directory site"]
