import { scenarios } from '../data/drivingScenarios.js';

const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const generalAnswers = [
  {
    match: /\b(pedestrian|crosswalk|crossing)\b/,
    answer: 'Stop and yield to a pedestrian in the crosswalk. Wait until the pedestrian has cleared your path before proceeding.',
    reminder: 'Check all crosswalks and follow local pedestrian right-of-way laws.',
  },
  {
    match: /\b(left turn|turning left|oncoming)\b/,
    answer: 'Yield to oncoming traffic going straight or turning right before making a left turn.',
    reminder: 'Signal, check for pedestrians, and turn only when the path is clear. Follow local rules.',
  },
  {
    match: /\bparallel park(?:ing)?\b/,
    answer: 'Signal and check around you, then line up beside the space. Back in slowly while turning toward the curb, straighten as you enter, and leave safe clearance from nearby vehicles.',
    reminder: 'Use mirrors and shoulder checks, move slowly, and follow local parking rules.',
  },
  {
    match: /\b(change lanes?|lane change|merge)\b/,
    answer: 'Check mirrors, signal, check your blind spot, and move only when there is a safe gap. Keep a steady speed and cancel your signal once established.',
    reminder: 'A signal does not give you the right-of-way. Follow local rules and avoid sudden moves.',
  },
  {
    match: /\b(yellow|amber)\b|\btraffic light\b/,
    answer: 'A steady yellow warns that the signal is changing. Stop if you can do so safely; if you are too close to stop safely, proceed cautiously.',
    reminder: 'Signal rules vary by location. Do not speed up to beat a red light.',
  },
];

function findScenario(question) {
  const normalized = question.toLowerCase().replace(/[–—]/g, '-');

  if (/\b(four[- ]way stop|stop sign|right[- ]of[- ]way)\b/.test(normalized)) {
    return scenarios.find(({ id }) => id === 'four_way_stop');
  }

  return null;
}

export async function askMockCoach(question) {
  await delay(350);

  const scenario = findScenario(question);
  if (scenario) {
    return {
      answer: scenario.response,
      reminder: scenario.reminder,
      visualization: {
        scenario_id: scenario.id,
        animation: 'demonstrate_right_of_way',
      },
    };
  }

  const generalAnswer = generalAnswers.find(({ match }) => match.test(question));
  if (generalAnswer) {
    return {
      answer: generalAnswer.answer,
      reminder: generalAnswer.reminder,
      visualization: null,
    };
  }

  return {
    answer: 'I can help with four-way stops, turning, pedestrians, parking, lane changes, and traffic signals. Try one of the suggested questions to see a practice example.',
    reminder: 'This local demo uses prepared examples, not an AI model or official driving manual.',
    visualization: null,
  };
}
