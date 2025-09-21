FROM node:lts-buster

WORKDIR /usr/src/app

COPY ./app/package.json /usr/src/app
COPY ./app/package-lock.json /usr/src/app

RUN npm ci

COPY ./app /usr/src/app

EXPOSE 3000

CMD ["npm", "start"]