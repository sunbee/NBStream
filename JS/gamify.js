hide = () => {
    document.getElementById('Content') .style.display='none'
}

show = () => {
    document.getElementById('Content') .style.display='block'
}

class Observable {
    constructor(value) {
        this._value = value;
        this._listeners = [];   
    }
    
    subscribe(listener) {
        this._listeners.push(listener);
    }
    
    notify() {
        this._listeners.forEach(listener => listener(this._value));
    }
    
    get value() {
        return this._value;
    }
    
    set value(val) {
        if (this._value != val) {
            this._value = val;
            this.notify();
        }
    }
} 

class Computed extends Observable {
    constructor (computer, dependents) {
        super(computer());  // Initialize computed value 
                            // by call to constructor of Observable class
        const listener = (_) => {
        /*
        Bridges between subscribers of a Computed instance 
        and the Observables in its list. The Computed instance must 
        operate as both listener and notifier to serve as go-between.
        The dual role is achieved through this function, which becomes 
        subscriber to each of the listed Observables. 
        When any Observable changes state, this function recomputes 
        state and notifies subscribers.  
        */
        console.log('Listener in Computed got ' + _);
        this._value = computer();
        console.log('Computer in Computed got ' + this._value);
        this.notify();  // Notify listeners of 'this' instance 
                        // of Computed class
        
        }
        dependents.forEach(dependent => dependent.subscribe(listener));    
    }
    
    get value() {
        return this._value;
    }

    set value(_) {
        /*
        Raise an exception, the value is computed from dependents, 
        not set.
        */
        throw "Set no computed property.";
    } 
}

const bind2DOM = (input, observed) => {
    /*
    Bind a DOM element of type input to data,
    with data wrapped in an instance of Observable class,
    so that any change to data updates the DOM and
    any change to the DOM updates the data (i.e. Observable instance).
    */
    observed.subscribe(() => input.value = observed.value);
    switch (input.nodeName) {
        case 'INPUT':
        input.onkeyup = () => {
            observed.value = input.value; 
            console.log(input.nodeName + " | " + observed.value); 
        }
        break;
        case 'SELECT':
        input.onchange = () => {
            observed.value = input.value; 
            console.log(input.nodeName + " | " + observed.value);
        }
        break;
        default:
        console.log(input.nodeName + " | " + observed.value);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    /* 
    Flow: 
    answers[i] UI > entries[i] OBS, targets[i] OBS > results[i] COMP > displays[i] UI 

    Note that the piece of data that is the expected answer to compare with the given answer
    is wrapped in an observable and stashed in the array 'targets'. This array matches the
    given answers in array 'entries'. The Computed needs the pair to evaluate the result.
    Accordingly, an instance of Computed receives both Observables in the list. The Computed's
    computer is tuned accordingly via the function factory. In this way, the HTML in each panel 
    is isolated and tag-collision is avoided.
    */
    // Define number of panels e.g. 2 ~[0, 1]
    panels = [0, 1, 2]
    // Get text-boxes for input by class-name
    answers = document.getElementsByClassName("Response");
    // Define array with an Observable for each text-box
    entries = [];
    panels.forEach(panel => entries.push(new Observable(panel)));
    // Get answers
    targets = [];
    Expected = Array.from(document.getElementsByClassName("Expected"));
    Expected.forEach(expected => targets.push(new Observable(expected.getAttribute("data-answer"))));
    // Get explanations
    explanations = []
    Elaboration = Array.from(document.getElementsByClassName("Elaboration"));
    Elaboration.forEach(elaboration => explanations.push(new Observable(elaboration.innerHTML)))
    console.log(explanations)
    // Get text-boxes for result by class-name
    displays = document.getElementsByClassName("Passfail");
    // Define array with a Computed for each display chaining with an Obs
    results = [];
    var funFactory = (entry, target, explanation) => {
        var out = () => { 
            console.log("Computer got expected as " + target.value);
            console.log("Computer got observed as " + entry.value);
            console.log("Computer got explanation as " + explanation.value)

            document.getElementById("Explanation").innerHTML = explanation.value;
            return (entry.value == target.value) ? "You nailed it!" : "Naaah, try again!"};
        return out
    } 
    panels.forEach(panel => { 
        results.push(new Computed(funFactory(entries[panel], targets[panel], explanations[panel]), 
                    [entries[panel], targets[panel], explanations[panel]]));
    })
    // Traverse the array and make bindings:
    //  Selector UI > [Bind2DOM] > Obs > [Chain] > Comp > [Bind2DOM] > Display UI
    panels.forEach(panel => {
        bind2DOM(answers[panel], entries[panel]);
        bind2DOM(displays[panel], results[panel]);
    })
});